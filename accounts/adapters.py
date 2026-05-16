from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
import logging
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup
    """
    
    def generate_unique_username(self, email):
        """Generate a unique username from email"""
        base_username = email.split('@')[0]
        # Remove special characters
        base_username = ''.join(c for c in base_username if c.isalnum() or c == '_')
        if not base_username:
            base_username = 'user'
        
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username[:150]  # Truncate to max length
    
    def save_user(self, request, sociallogin, form=None):
        """Override save_user to handle email-based user creation with username"""
        user_data = sociallogin.account.extra_data
        email = user_data.get('email', '')
        
        # Generate a unique username
        username = self.generate_unique_username(email)
        
        # Create user
        user = User(
            email=email,
            username=username,
            first_name=user_data.get('given_name', ''),
            last_name=user_data.get('family_name', ''),
            is_active=True,
        )
        user.set_unusable_password()
        user.save()
        
        sociallogin.user = user
        sociallogin.save(request)
        
        logger.info(f"Google user created: {user.email} (username: {user.username})")
        
        return user
    
    def pre_social_login(self, request, sociallogin):
        """Connect social account to existing user if email matches"""
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                existing_user = User.objects.get(email=email)
                sociallogin.connect(request, existing_user)
                logger.info(f"Connected Google account to existing user: {email}")
            except User.DoesNotExist:
                pass
        
        return None