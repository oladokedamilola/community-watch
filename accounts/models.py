from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom User model using email as username"""
    # Personal info
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True) 
    
    # Role flags
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Profile info
    village = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_role(self):
        return "Admin" if self.is_admin else "Community Member"


class Profile(models.Model):
    """Profile model for all users to store profile pictures and other shared data"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    village = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.email}"

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-avatar.jpg'


class EmailVerification(models.Model):
    """Model to handle email verification tokens"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='email_verification'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def __str__(self):
        return f"Verification for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class PasswordReset(models.Model):
    """Model to handle password reset tokens"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='password_resets'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset"
        verbose_name_plural = "Password Resets"

    def __str__(self):
        return f"Password reset for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiry_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class RateLimit(models.Model):
    """Rate limiting for various actions"""
    ACTION_CHOICES = (
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('password_change', 'Password Change'),
        ('password_setup', 'Password Setup'),
    )
    
    email = models.EmailField(db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    attempt_count = models.IntegerField(default=0)
    first_attempt = models.DateTimeField(auto_now_add=True)
    last_attempt = models.DateTimeField(auto_now=True)
    blocked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('email', 'action')
        verbose_name = "Rate Limit"
        verbose_name_plural = "Rate Limits"

    def __str__(self):
        return f"{self.email} - {self.action}"

    @classmethod
    def check_rate_limit(cls, email, action):
        """Check if an action is rate limited"""
        rate_limit, created = cls.objects.get_or_create(
            email=email,
            action=action,
            defaults={'first_attempt': timezone.now()}
        )
        
        if rate_limit.blocked_until and rate_limit.blocked_until > timezone.now():
            minutes_remaining = int((rate_limit.blocked_until - timezone.now()).total_seconds() / 60)
            return False, {
                'blocked': True,
                'minutes_remaining': minutes_remaining,
                'blocked_until': rate_limit.blocked_until,
                'attempts': rate_limit.attempt_count
            }
        
        if rate_limit.blocked_until and rate_limit.blocked_until <= timezone.now():
            rate_limit.blocked_until = None
            rate_limit.attempt_count = 0
            rate_limit.save()
        
        window_hours = getattr(settings, 'RATE_LIMIT_WINDOW_HOURS', 1)
        max_attempts = getattr(settings, 'RATE_LIMIT_MAX_ATTEMPTS', 3)
        
        time_window_start = timezone.now() - timedelta(hours=window_hours)
        
        if rate_limit.first_attempt < time_window_start:
            rate_limit.attempt_count = 0
            rate_limit.first_attempt = timezone.now()
            rate_limit.save()
        
        if rate_limit.attempt_count >= max_attempts:
            block_hours = getattr(settings, 'RATE_LIMIT_BLOCK_HOURS', 1)
            rate_limit.blocked_until = timezone.now() + timedelta(hours=block_hours)
            rate_limit.save()
            
            minutes_remaining = block_hours * 60
            return False, {
                'blocked': True,
                'minutes_remaining': minutes_remaining,
                'blocked_until': rate_limit.blocked_until,
                'attempts': rate_limit.attempt_count
            }
        
        return True, {
            'blocked': False,
            'attempts': rate_limit.attempt_count,
            'remaining': max_attempts - rate_limit.attempt_count
        }
    
    def increment_attempt(self):
        self.attempt_count += 1
        self.last_attempt = timezone.now()
        self.save()
    
    def reset_attempts(self):
        self.attempt_count = 0
        self.blocked_until = None
        self.first_attempt = timezone.now()
        self.save()
        
class PasswordSetup(models.Model):
    """Model to handle password setup for social auth users"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='password_setup'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Setup"
        verbose_name_plural = "Password Setups"

    def __str__(self):
        return f"Password setup for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiry_hours = getattr(settings, 'PASSWORD_SETUP_TOKEN_EXPIRY_HOURS', 24)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()