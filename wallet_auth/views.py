import json
import secrets
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, get_user_model
from django.utils import timezone
from web3 import Web3
from eth_account.messages import encode_defunct
from django.contrib.auth.hashers import make_password

from .models import WalletProfile

# Create a Web3 instance (no provider needed for account recovery)
w3 = Web3()

logger = logging.getLogger(__name__)
User = get_user_model()


@csrf_exempt
def get_nonce(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        address = data.get('address')
        if not address or not Web3.is_address(address):
            return JsonResponse({'error': 'Invalid address'}, status=400)

        address = Web3.to_checksum_address(address)
        nonce = secrets.token_hex(32)

        # Use full address as username to avoid collisions
        username = address
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'password': make_password(None)}
        )
        # If the user already exists but has an empty/null password, fix it
        if not created and (not user.password or user.password == ''):
            user.password = make_password(None)
            user.save()

        profile, created = WalletProfile.objects.get_or_create(
            wallet_address=address,
            defaults={'user': user}
        )
        # Ensure the user is linked if profile existed with a different user
        if profile.user != user:
            profile.user = user
            profile.save()

        profile.nonce = nonce
        profile.nonce_created_at = timezone.now()
        profile.save()

        return JsonResponse({'nonce': nonce})

    except Exception as e:
        logger.error(f"Nonce error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def verify_signature(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        address = data.get('address')
        signature = data.get('signature')

        if not address or not signature:
            return JsonResponse({'error': 'Missing address or signature'}, status=400)

        # Ensure signature has 0x prefix (MetaMask always includes it, but just in case)
        if not signature.startswith('0x'):
            signature = '0x' + signature

        address = Web3.to_checksum_address(address)

        try:
            profile = WalletProfile.objects.get(wallet_address=address)
        except WalletProfile.DoesNotExist:
            return JsonResponse({'error': 'Wallet not registered'}, status=404)

        nonce = profile.nonce
        if not nonce:
            return JsonResponse({'error': 'No nonce pending'}, status=400)

        # Nonce expires after 5 minutes
        if (timezone.now() - profile.nonce_created_at).seconds > 300:
            return JsonResponse({'error': 'Nonce expired. Please refresh and try again.'}, status=400)

        # ========== FIX: Convert nonce to UTF-8 hex (matches frontend's utf8ToHex) ==========
        # The frontend signs: "0x" + hex-encoded UTF-8 bytes of the nonce string
        nonce_bytes = nonce.encode('utf-8')
        nonce_hex = '0x' + nonce_bytes.hex()

        try:
            message = encode_defunct(hexstr=nonce_hex)
            recovered = w3.eth.account.recover_message(message, signature=signature)
        except Exception as e:
            logger.error(f"Recovery error: {e}")
            return JsonResponse({'error': f'Invalid signature format: {str(e)}'}, status=400)

        # Compare (case-insensitive)
        if recovered.lower() != address.lower():
            logger.warning(f"Address mismatch: recovered={recovered}, expected={address}")
            return JsonResponse({'error': 'Signature does not match the wallet address'}, status=400)

        # Success – log the user in
        user = profile.user
        # FIX: specify the backend explicitly because we have multiple backends
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Invalidate the nonce
        profile.nonce = None
        profile.nonce_created_at = None
        profile.save()

        return JsonResponse({'success': True, 'username': user.username})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return JsonResponse({'error': str(e)}, status=500)