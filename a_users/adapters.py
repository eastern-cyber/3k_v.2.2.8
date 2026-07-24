# a_users/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import login

User = get_user_model()

class socialSignupAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """Called before a social login is completed"""
        for _ in messages.get_messages(request): 
            pass
        
        # If user already exists, connect the social account
        if sociallogin.is_existing:
            return
        
        # Check if user already exists with this email
        try:
            email = sociallogin.user.email
            if email:
                try:
                    user = User.objects.get(email=email)
                    # Connect social account to existing user
                    sociallogin.connect(request, user)
                    messages.success(request, f"ยินดีต้อนรับกลับ {user.username}!")
                    return
                except User.DoesNotExist:
                    # User doesn't exist, will create new account
                    pass
        except:
            pass
        
        # If no user found, let the normal signup flow continue
        return
    
    def populate_user(self, request, sociallogin, data):
        """Populate user data from social provider"""
        user = super().populate_user(request, sociallogin, data)
        
        # Set username from email if username is empty
        if not user.username and user.email:
            base_username = user.email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user.username = username
        
        # Set name if available
        if not user.first_name and data.get('first_name'):
            user.first_name = data.get('first_name')
        if not user.last_name and data.get('last_name'):
            user.last_name = data.get('last_name')
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """Save user with additional logic"""
        user = super().save_user(request, sociallogin, form)
        
        # Set user as active
        user.is_active = True
        user.save()
        
        messages.success(request, f"🎉 ยินดีต้อนรับ {user.username}!")
        
        return user