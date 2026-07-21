import os
import random
import time
import requests
from threading import Thread

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model, logout, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Count
from django.core.validators import validate_email
from django.core.cache import cache
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect

from allauth.account.models import EmailAddress
from allauth.account.forms import SignupForm
from allauth.account.utils import perform_login

from .forms import ProfileForm, EmailForm, BirthdayForm

User = get_user_model()


# ============================================================================
# OTP Email Functions (Mailgun API)
# ============================================================================

def get_otp_email_content(code):
    """Generate HTML and plain text email content for OTP verification"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ยืนยันอีเมลของคุณ</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1a1a1a; background-color: #f5f5f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #EC4899, #8B5CF6); padding: 32px 24px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 22px; font-weight: 600; }}
            .content {{ padding: 32px 28px; }}
            .otp-container {{ background: #f8fafc; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0; border: 2px dashed #e2e8f0; }}
            .otp-code {{ font-size: 36px; font-weight: 700; letter-spacing: 10px; color: #EC4899; font-family: 'Courier New', monospace; }}
            .info {{ color: #64748b; font-size: 14px; text-align: center; margin: 16px 0; }}
            .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 8px; font-size: 14px; color: #92400e; margin: 20px 0; }}
            .footer {{ background: #f8fafc; padding: 20px 24px; text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>🔐 ยืนยันอีเมลของคุณ</h1></div>
            <div class="content">
                <p style="font-size: 18px; font-weight: 500; margin-bottom: 16px;">สวัสดี,</p>
                <p>คุณได้ลงทะเบียนใช้งาน KokKokKok กรุณากรอกรหัสยืนยันด้านล่าง:</p>
                <div class="otp-container"><div class="otp-code">{code}</div></div>
                <div class="info">⏱️ รหัสนี้จะหมดอายุใน <strong>5 นาที</strong></div>
                <div class="warning"><strong>⚠️ คำเตือน:</strong> อย่าแชร์รหัสนี้กับผู้อื่น</div>
                <p style="margin-top: 24px; color: #64748b; font-size: 14px;">หากคุณไม่ได้เป็นผู้ขอรหัสนี้ กรุณาเพิกเฉยต่ออีเมลนี้</p>
            </div>
            <div class="footer"><p>© 2026 KokKokKok. All rights reserved.</p></div>
        </div>
    </body>
    </html>
    """
    
    plain_text = f"""
    สวัสดี,

    คุณได้ลงทะเบียนใช้งาน KokKokKok กรุณาใช้รหัสยืนยันนี้:

    รหัส: {code}

    รหัสนี้จะหมดอายุใน 5 นาที

    หากคุณไม่ได้เป็นผู้ขอรหัสนี้ กรุณาเพิกเฉยต่ออีเมลนี้

    — ทีมงาน KokKokKok
    """
    
    return html_content, plain_text


def send_otp_email(email, code):
    """Send OTP using Resend API"""
    
    api_key = os.getenv('RESEND_API_KEY', '')
    
    if not api_key:
        print("❌ RESEND_API_KEY not set - email not sent")
        return False
    
    html_content, plain_text = get_otp_email_content(code)
    
    # Resend API
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "from": "KokKokKok <noreply@mail.3kok.app>",  # Resend's default domain
        "to": [email],
        "subject": "🔐 รหัสยืนยัน KokKokKok",
        "html": html_content,
        "text": plain_text,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Resend: Email sent to {email}")
            return True
        else:
            print(f"❌ Resend error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Resend request failed: {e}")
        return False


# ============================================================================
# OTP Verification View
# ============================================================================

def verification_code(request):
    """Send OTP via HTMX request"""
    email = request.GET.get("email")
    
    if not email:
        return HttpResponse('<p class="text-rose-500 text-sm">⚠️ กรุณากรอกอีเมล</p>')
    
    # Rate limiting: 1 request per 60 seconds
    rate_key = f"otp_rate_{email}"
    if cache.get(rate_key):
        return HttpResponse('<p class="text-rose-500 text-sm">⚠️ กรุณารอ 60 วินาทีก่อนขอรหัสใหม่</p>')
    
    # Validate email format
    try:
        validate_email(email)
    except:
        return HttpResponse('<p class="text-rose-500 text-sm">⚠️ อีเมลไม่ถูกต้อง</p>')
    
    # Check if email already registered
    if User.objects.filter(email=email).exists():
        return HttpResponse('<p class="text-rose-500 text-sm">⚠️ อีเมลนี้ถูกใช้งานแล้ว</p>')
    
    # Generate and store OTP
    code = str(random.randint(100000, 999999))
    cache.set(f"verification_code_{email}", code, timeout=300)  # 5 minutes
    cache.set(f"otp_attempts_{email}", 0, timeout=300)
    cache.set(rate_key, True, 60)  # Rate limit: 60 seconds
    
    # Send email using Mailgun API (non-blocking)
    Thread(target=send_otp_email, args=(email, code)).start()
    
    return HttpResponse("""
        <div class="text-emerald-600 text-sm flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            <span>✅ ส่งรหัสเรียบร้อย! ตรวจสอบอีเมล</span>
        </div>
    """)


# ============================================================================
# Custom Signup with OTP Verification
# ============================================================================

@csrf_protect
def signup_otp_view(request):
    """Function-based signup with OTP verification"""
    
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            entered_code = request.POST.get('code', '').strip()
            
            # Validate OTP
            if not entered_code:
                messages.error(request, '⚠️ กรุณากรอกรหัสยืนยันที่ส่งไปทางอีเมล')
                return render(request, 'account/signup.html', {'form': form})
            
            stored_code = cache.get(f"verification_code_{email}")
            attempts = cache.get(f"otp_attempts_{email}", 0)
            
            if not stored_code:
                messages.error(request, '⚠️ รหัสหมดอายุหรือไม่ถูกต้อง กรุณาขอรหัสใหม่')
                return render(request, 'account/signup.html', {'form': form})
            
            if attempts >= 3:
                messages.error(request, '⚠️ ผิดพลาดเกิน 3 ครั้ง กรุณาขอรหัสใหม่')
                cache.delete(f"verification_code_{email}")
                return render(request, 'account/signup.html', {'form': form})
            
            if stored_code != entered_code:
                cache.set(f"otp_attempts_{email}", attempts + 1, timeout=300)
                remaining = 3 - (attempts + 1)
                messages.error(request, f'⚠️ รหัสไม่ถูกต้อง เหลือโอกาส {remaining} ครั้ง')
                return render(request, 'account/signup.html', {'form': form})
            
            # OTP verified - create user
            user = form.save(request)
            user.is_active = True
            user.save()
            
            # Clean up cache
            cache.delete(f"verification_code_{email}")
            cache.delete(f"otp_attempts_{email}")
            
            # Log the user in
            perform_login(request, user, 'django.contrib.auth.backends.ModelBackend')
            
            messages.success(request, '🎉 ลงทะเบียนสำเร็จ! ยินดีต้อนรับสู่ KokKokKok')
            
            return redirect(request.GET.get('next', '/'))
    else:
        form = SignupForm()
    
    return render(request, 'account/signup.html', {'form': form})


# ============================================================================
# Other Views (unchanged)
# ============================================================================

def index_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'a_users/index.html')


@login_required
def profile_view(request, username=None):
    if not username:
        return redirect('profile', request.user.username)
    
    profile_user = get_object_or_404(User, username=username)
    
    if request.GET.get('link'):
        urlpath = reverse('profile', kwargs={'username': username})
        return render(request, 'a_users/partials/_profile_link.html', {"urlpath": urlpath})
    
    if request.GET.get("following"):
        accounts = User.objects.filter(is_followed__follower=profile_user)
        return render(request, 'a_users/partials/_profile_following.html', {'accounts': accounts})
    
    if request.GET.get("followers"):
        accounts = User.objects.filter(is_follower__following=profile_user)
        return render(request, 'a_users/partials/_profile_following.html', {'accounts': accounts, 'followers': True})
    
    if request.GET.get('reposted'):
        profile_reposts = profile_user.repostedposts.order_by('-repost__created_at')
        return render(request, 'a_users/partials/_profile_posts_reposted.html', {'profile_reposts': profile_reposts})
    
    if request.GET.get('liked'):
        profile_posts_liked = profile_user.likedposts.all().order_by('-likedpost__created_at')
        return render(request, 'a_users/partials/_profile_posts_liked.html', {'profile_posts_liked': profile_posts_liked})
    
    if request.GET.get('bookmarked'):
        profile_posts_bookmarked = request.user.bookmarkedposts.all().order_by('-bookmarkedpost__created_at')
        return render(request, 'a_users/partials/_profile_posts_bookmarked.html', {'profile_posts_bookmarked': profile_posts_bookmarked})
    
    sort_order = request.GET.get('sort', '')
    if sort_order == 'oldest':
        profile_posts = profile_user.posts.order_by('created_at')
    elif sort_order == 'popular':
        profile_posts = profile_user.posts.annotate(num_likes=Count('likes')).order_by('-num_likes', '-created_at')
    else:
        profile_posts = profile_user.posts.order_by('-created_at')
    
    profile_user_likes = profile_user.posts.aggregate(total_likes=Count('likes'))['total_likes']
    
    context = {
        'page': 'Profile',
        'profile_user': profile_user,
        'profile_user_likes': profile_user_likes,
        'profile_posts': profile_posts,
    }
    
    if request.GET.get('sort'):
        return render(request, 'a_users/partials/_profile_posts.html', context)
    
    if request.htmx:
        return render(request, 'a_users/partials/_profile.html', context)
    return render(request, 'a_users/profile.html', context)


@login_required
def profile_edit(request):
    form = ProfileForm(instance=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile', request.user.username)
    
    if request.htmx:
        return render(request, "a_users/partials/_profile_edit.html", {'form': form})
    return redirect('profile', request.user.username)


@login_required
def settings_view(request):
    form = EmailForm(instance=request.user)
    
    if request.GET.get('email'):
        return render(request, 'a_users/partials/_settings_email.html', {'form': form})
    
    if request.POST.get("email"):
        form = EmailForm(request.POST, instance=request.user)
        current_email = request.user.email
        
        if form.is_valid():
            new_email = form.cleaned_data['email']
            if new_email != current_email:
                form.save()
                email_obj = EmailAddress.objects.get(user=request.user, primary=True)
                email_obj.email = new_email
                email_obj.verified = False
                email_obj.save()
                return redirect('settings')
    
    if request.GET.get('verification'):
        return render(request, 'a_users/partials/_settings_verification.html')
    
    if request.POST.get("code"):
        code = request.POST.get('code').strip()
        email = request.user.email
        cached_code = cache.get(f"verification_code_{email}")
        if cached_code and cached_code == code:
            email_obj = EmailAddress.objects.get(user=request.user, primary=True)
            email_obj.verified = True
            email_obj.save()
            return redirect('settings')
    
    if request.GET.get('birthday'):
        birthdayform = BirthdayForm(instance=request.user)
        return render(request, 'a_users/partials/_settings_birthday.html', {'form': birthdayform})
    
    if request.POST.get("birthday"):
        birthdayform = BirthdayForm(request.POST, instance=request.user)
        if birthdayform.is_valid():
            birthdayform.save()
            return redirect('settings')
    
    if request.POST.get("notifications"):
        request.user.notifications = request.POST.get("notifications") == 'on'
        request.user.save()
        return HttpResponse('')
    
    if request.GET.get("darkmode"):
        request.user.darkmode = request.GET.get("darkmode") == 'true'
        request.user.save()
        return HttpResponse('')
    
    if request.htmx:
        return render(request, "a_users/partials/_settings.html", {'form': form})
    return render(request, "a_users/settings.html", {'form': form})


@login_required
def delete_account(request):
    user = request.user
    if request.method == "POST":
        logout(request)
        user.delete()
        return redirect('index')
    
    return render(request, 'a_users/profile_delete.html')