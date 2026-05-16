import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] Loaded .env from: {env_path}")

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here-change-in-production')

DEBUG = True

ALLOWED_HOSTS = ['*']  # Update for production

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    
    # Custom apps
    'accounts.apps.AccountsConfig',
    'reports',
    
    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'pwa',  # PWA support
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Allauth middleware
]

ROOT_URLCONF = 'gridwatch_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gridwatch_project.wsgi.application'

# ============================================================================
# DATABASE - SQLite for development
# ============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================================
# CUSTOM USER MODEL
# ============================================================================
AUTH_USER_MODEL = 'accounts.CustomUser'

# ============================================================================
# AUTHENTICATION BACKENDS
# ============================================================================
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailAuthBackend',  # Custom email authentication
    'allauth.account.auth_backends.AuthenticationBackend',  # Allauth backend
    'django.contrib.auth.backends.ModelBackend',  # Fallback
]

# ============================================================================
# DJANGO-ALLAUTH SETTINGS
# ============================================================================
SITE_ID = 1

# Authentication - use email only (NEW FORMAT)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

# Email verification
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Set to 'mandatory' for production
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[GridWatch] '
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True

# Login/Logout settings
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_SESSION_REMEMBER = True

# Password settings
ACCOUNT_PASSWORD_MIN_LENGTH = 8

# Redirect URLs
ACCOUNT_SIGNUP_REDIRECT_URL = 'accounts:pending_verification'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'accounts:pending_verification'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'accounts:pending_verification'

# ============================================================================
# SOCIAL ACCOUNT SETTINGS
# ============================================================================
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Google already verifies email
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'
ACCOUNT_INACTIVE_URL = 'accounts:pending_verification'

# Google OAuth Provider Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC & MEDIA FILES
# ============================================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('DJANGO_EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('DJANGO_EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER', '')  # Match the .env variable name
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD', '')  # Match the .env variable name
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'GridWatch <noreply@gridwatch.com>')

# ============================================================================
# SITE URL (For email links)
# ============================================================================
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')

# ============================================================================
# LOGIN/REDIRECT URLs
# ============================================================================
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard'  # Redirect to dashboard after login
LOGOUT_REDIRECT_URL = 'home'

# ============================================================================
# TOKEN EXPIRY SETTINGS
# ============================================================================
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 1
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

PASSWORD_SETUP_TOKEN_EXPIRY_HOURS = 24
# ============================================================================
# RATE LIMITING SETTINGS
# ============================================================================
RATE_LIMIT_MAX_ATTEMPTS = 3
RATE_LIMIT_BLOCK_HOURS = 1
RATE_LIMIT_WINDOW_HOURS = 1

# ============================================================================
# PWA (Progressive Web App) SETTINGS
# ============================================================================
PWA_APP_NAME = 'GridWatch'
PWA_APP_DESCRIPTION = 'Monitor and report outages in rural communities'
PWA_APP_THEME_COLOR = '#2E7D32'
PWA_APP_BACKGROUND_COLOR = '#FFFFFF'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = '#2E7D32'
PWA_APP_ICONS = [
    {'src': '/static/images/icons/icon-72x72.png', 'sizes': '72x72', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-96x96.png', 'sizes': '96x96', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-128x128.png', 'sizes': '128x128', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-144x144.png', 'sizes': '144x144', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-152x152.png', 'sizes': '152x152', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-192x192.png', 'sizes': '192x192', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-384x384.png', 'sizes': '384x384', 'type': 'image/png'},
    {'src': '/static/images/icons/icon-512x512.png', 'sizes': '512x512', 'type': 'image/png'},
]
PWA_APP_ICONS_APPLE = [
    {'src': '/static/images/icons/icon-152x152.png', 'sizes': '152x152', 'type': 'image/png'},
]
PWA_APP_SPLASH_SCREEN = [
    {'src': '/static/images/icons/splash-640x1136.png', 'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'},
    {'src': '/static/images/icons/splash-750x1334.png', 'media': '(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)'},
    {'src': '/static/images/icons/splash-1242x2208.png', 'media': '(device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3)'},
    {'src': '/static/images/icons/splash-1125x2436.png', 'media': '(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)'},
]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'en'
PWA_APP_DEBUG_MODE = False

# Service Worker Path
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/js', 'serviceworker.js')

# ============================================================================
# HTTPS SETTINGS (for production)
# ============================================================================
SECURE_SSL_REDIRECT = False  # Set to True in production with HTTPS
SESSION_COOKIE_SECURE = False  # Set to True in production
CSRF_COOKIE_SECURE = False  # Set to True in production

# ============================================================================
# WEB PUSH NOTIFICATION SETTINGS
# ============================================================================
WEBPUSH_SETTINGS = {
    'VAPID_PUBLIC_KEY': os.getenv('VAPID_PUBLIC_KEY', ''),
    'VAPID_PRIVATE_KEY': os.getenv('VAPID_PRIVATE_KEY', ''),
    'VAPID_ADMIN_EMAIL': os.getenv('VAPID_ADMIN_EMAIL', 'admin@gridwatch.com'),
}

# ============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'