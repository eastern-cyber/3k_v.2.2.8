from django.urls import path
from .views import (
    profile_view, profile_edit, verification_code, 
    settings_view, delete_account,
    password_reset_request, password_reset_verify
)

app_name = 'a_users'

urlpatterns = [
    path('', profile_view),
    path('edit/', profile_edit, name='profile_edit'),
    path('verification_code/', verification_code, name='verification_code'),
    path('settings/', settings_view, name='settings'),
    path('delete_account/', delete_account, name='delete_account'),
    
    # Password Reset with OTP
    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset/verify/', password_reset_verify, name='password_reset_verify'),
]