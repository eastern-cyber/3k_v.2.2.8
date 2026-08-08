from django.conf import settings
from django.db import models

class WalletProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # Use the custom user model
        on_delete=models.CASCADE,
        related_name='wallet_profile'
    )
    wallet_address = models.CharField(max_length=42, unique=True, db_index=True)
    nonce = models.CharField(max_length=64, blank=True, null=True)
    nonce_created_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.wallet_address}"