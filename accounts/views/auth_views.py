# accounts/views/auth_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model  # Add this
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import IntegrityError
from django.urls import reverse
from django.conf import settings
import logging
import smtplib

from ..forms import (
    UserRegistrationForm,
    PasswordResetRequestForm,
    SetPasswordForm
)
from ..models import (
    Profile,
    EmailVerification,
    PasswordReset,
    RateLimit
)
from ..utils import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email
)

# Get the custom User model
User = get_user_model()

logger = logging.getLogger(__name__)


# Rate limit helper
def render_rate_limit_page(request, action, block_info):
    """Render rate limit exceeded page"""
    context = {
        'action': action,
        'action_display': dict(RateLimit.ACTION_CHOICES).get(action, action),
        'minutes_remaining': block_info.get('minutes_remaining', 0),
        'blocked_until': block_info.get('blocked_until'),
        'attempts': block_info.get('attempts', 0),
    }
    return render(request, 'accounts/rate_limit_exceeded.html', context, status=429)


# ============================================================================
# REGISTRATION AND VERIFICATION VIEWS
# ============================================================================

def register_view(request):
    """Handle user registration with email verification requirement"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create user but set as inactive until email verification
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                # Create email verification record
                verification = EmailVerification.objects.create(user=user)

                # Send verification email
                try:
                    send_verification_email(user, verification)
                    logger.info(f"Verification email sent to {user.email}")

                    request.session['pending_verification_email'] = user.email

                    messages.success(
                        request,
                        f"Account created! We've sent a verification link to {user.email}."
                    )
                    messages.info(
                        request,
                        "Please check your inbox (and spam folder) and click the link to activate your account."
                    )

                    return redirect('accounts:pending_verification')

                except (ConnectionRefusedError, smtplib.SMTPException, TimeoutError) as e:
                    logger.error(f"Email sending failed for {user.email}: {str(e)}")
                    user.delete()

                    messages.error(
                        request,
                        "We're having trouble with our email system right now. Please try again in a few minutes."
                    )
                    return redirect('accounts:register')

            except IntegrityError as e:
                logger.error(f"Integrity error creating user: {str(e)}")
                messages.error(request, "This email is already registered. Please log in instead.")
                return redirect('accounts:login')

            except Exception as e:
                logger.error(f"Unexpected error in registration: {str(e)}", exc_info=True)
                messages.error(request, "An unexpected error occurred. Please try again.")
                return redirect('accounts:register')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_email_view(request, token):
    """Verify user's email address and activate account"""
    logger.info(f"Email verification attempt with token: {token}")

    try:
        verification = get_object_or_404(EmailVerification, token=token, is_used=False)

        if not verification.is_valid():
            logger.warning(f"Expired verification token: {token}")
            messages.error(
                request,
                "This verification link has expired. Please request a new one."
            )
            return redirect('accounts:resend_verification')

        user = verification.user
        user.is_active = True
        user.save()

        verification.is_used = True
        verification.save()

        logger.info(f"User {user.email} verified successfully")

        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")

        # Log the user in
        login(request, user, backend='accounts.backends.EmailAuthBackend')

        messages.success(request, "Your email has been verified successfully! You are now logged in.")

        return redirect('dashboard')

    except Exception as e:
        logger.error(f"Error in email verification: {str(e)}", exc_info=True)
        messages.error(request, "Invalid verification link. Please request a new one.")
        return redirect('accounts:resend_verification')


def resend_verification_view(request):
    """Resend verification email with rate limiting"""
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            messages.error(request, "Please provide an email address.")
            return redirect('accounts:resend_verification')

        # Check rate limit
        is_allowed, block_info = RateLimit.check_rate_limit(email, 'email_verification')

        if not is_allowed:
            return render_rate_limit_page(request, 'email_verification', block_info)

        try:
            user = User.objects.get(email=email, is_active=False)

        except User.DoesNotExist:
            try:
                user = User.objects.get(email=email, is_active=True)
                messages.info(request, "This account is already verified. Please log in.")
                return redirect('accounts:login')

            except User.DoesNotExist:
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='email_verification'
                )
                rate_limit.increment_attempt()

                messages.success(request, "If an account exists, a verification email has been sent.")
                return redirect('accounts:login')

        # Handle existing inactive user
        try:
            verification = EmailVerification.objects.filter(
                user=user,
                is_used=False
            ).first()

            if verification and verification.is_valid():
                token = verification.token
                logger.info(f"Reusing existing valid token for {email}")
            else:
                if verification:
                    verification.is_used = True
                    verification.save()

                verification = EmailVerification.objects.create(user=user)
                token = verification.token
                logger.info(f"Created new verification token for {email}")

            try:
                send_verification_email(user, verification)
                logger.info(f"Verification email sent to {email}")

                RateLimit.objects.filter(email=email, action='email_verification').delete()

                request.session['pending_verification_email'] = user.email

                messages.success(
                    request,
                    f"A verification email has been sent to {email}. Please check your inbox."
                )
                return redirect('accounts:pending_verification')

            except Exception as e:
                logger.error(f"Failed to send verification email to {email}: {str(e)}", exc_info=True)

                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='email_verification'
                )
                rate_limit.increment_attempt()

                messages.error(
                    request,
                    "There was a problem sending the verification email. Please try again later."
                )
                return redirect('accounts:resend_verification')

        except Exception as e:
            logger.error(f"Error in resend verification for {email}: {str(e)}", exc_info=True)

            rate_limit, created = RateLimit.objects.get_or_create(
                email=email,
                action='email_verification'
            )
            rate_limit.increment_attempt()

            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('accounts:resend_verification')

    initial_email = request.session.get('pending_verification_email', '')

    context = {
        'email': initial_email,
    }
    return render(request, "accounts/resend_verification.html", context)


def pending_verification_view(request):
    """Show page informing user that their email is pending verification"""
    email = request.session.get('pending_verification_email')

    if not email:
        return redirect('accounts:register')

    context = {
        'email': email,
        'resend_url': reverse('accounts:resend_verification')
    }
    return render(request, "accounts/pending_verification.html", context)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def login_view(request):
    """Email-based login view - handles regular users and social auth users without passwords"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'accounts/login.html')

        is_allowed, block_info = RateLimit.check_rate_limit(email, 'login')

        if not is_allowed:
            return render_rate_limit_page(request, 'login', block_info)

        try:
            user = User.objects.get(email=email)

            # Check if user is not active (email not verified)
            if not user.is_active:
                verification = EmailVerification.objects.filter(
                    user=user,
                    is_used=False
                ).first()

                if verification and verification.is_valid():
                    request.session['pending_verification_email'] = email
                    messages.warning(
                        request,
                        "Your email is not verified yet. Please check your inbox for the verification link."
                    )
                    return redirect('accounts:pending_verification')
                else:
                    if verification:
                        verification.is_used = True
                        verification.save()

                    new_verification = EmailVerification.objects.create(user=user)
                    send_verification_email(user, new_verification)

                    request.session['pending_verification_email'] = email
                    messages.info(
                        request,
                        "A new verification email has been sent. Please verify your email to log in."
                    )
                    return redirect('accounts:pending_verification')

            # Check if user is a social auth user (has no password)
            if not user.has_usable_password():
                # Social auth user - redirect to password setup flow
                # Check for existing valid token
                existing_setup = PasswordSetup.objects.filter(
                    user=user,
                    is_used=False
                ).first()

                if not existing_setup or not existing_setup.is_valid():
                    if existing_setup:
                        existing_setup.is_used = True
                        existing_setup.save()

                    password_setup = PasswordSetup.objects.create(user=user)
                else:
                    password_setup = existing_setup

                # Send password setup email
                try:
                    from ..utils import send_password_setup_email
                    send_password_setup_email(user, password_setup)

                    messages.info(
                        request,
                        f"Your account was created with Google. We've sent a link to {email} to set up a password for email login."
                    )
                    return redirect('accounts:login')
                except Exception as e:
                    logger.error(f"Failed to send password setup email: {str(e)}")
                    messages.error(
                        request,
                        "There was an error. Please use 'Forgot Password' to set up your password."
                    )
                    return redirect('accounts:login')

        except User.DoesNotExist:
            pass

        # Authenticate regular user
        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_active:
            RateLimit.objects.filter(email=email, action='login').delete()

            login(request, user)

            if remember_me:
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {user.first_name or user.email}!')

            return redirect('dashboard')
        else:
            rate_limit, created = RateLimit.objects.get_or_create(
                email=email,
                action='login'
            )
            rate_limit.increment_attempt()

            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Log out the current user"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')


# ============================================================================
# PASSWORD MANAGEMENT VIEWS
# ============================================================================

def password_reset_request_view(request):
    """Request password reset email with rate limiting - also handles social auth users"""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            is_allowed, block_info = RateLimit.check_rate_limit(email, 'password_reset')

            if not is_allowed:
                return render_rate_limit_page(request, 'password_reset', block_info)

            try:
                user = User.objects.get(email=email, is_active=True)

                # Check if user is a social auth user (no password)
                if not user.has_usable_password():
                    # Send password setup email instead of password reset
                    from ..models import PasswordSetup
                    from ..utils import send_password_setup_email

                    existing_setup = PasswordSetup.objects.filter(
                        user=user,
                        is_used=False
                    ).first()

                    if not existing_setup or not existing_setup.is_valid():
                        if existing_setup:
                            existing_setup.is_used = True
                            existing_setup.save()

                        password_setup = PasswordSetup.objects.create(user=user)
                    else:
                        password_setup = existing_setup

                    send_password_setup_email(user, password_setup)

                    RateLimit.objects.filter(email=email, action='password_reset').delete()

                    messages.success(
                        request,
                        "Your account was created with Google. A password setup link has been sent to your email."
                    )
                    return redirect('accounts:login')

                # Regular user - send password reset
                password_reset = PasswordReset.objects.create(user=user)

                try:
                    send_password_reset_email(user, password_reset)

                    RateLimit.objects.filter(email=email, action='password_reset').delete()

                    messages.success(
                        request,
                        "Password reset instructions have been sent to your email."
                    )
                    return redirect('accounts:login')

                except Exception as e:
                    logger.error(f"Failed to send password reset email: {str(e)}")

                    rate_limit, created = RateLimit.objects.get_or_create(
                        email=email,
                        action='password_reset'
                    )
                    rate_limit.increment_attempt()

                    messages.error(
                        request,
                        "There was an error sending the reset email. Please try again."
                    )
                    password_reset.is_used = True
                    password_reset.save()

            except User.DoesNotExist:
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='password_reset'
                )
                rate_limit.increment_attempt()

                messages.success(
                    request,
                    "If an account exists with this email, you'll receive reset instructions."
                )
                return redirect('accounts:login')
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_confirm_view(request, token):
    """Confirm password reset and set new password"""
    try:
        password_reset = PasswordReset.objects.get(token=token, is_used=False)

        if not password_reset.is_valid():
            messages.error(request, "The password reset link has expired. Please request a new one.")
            return redirect("accounts:password_reset_request")

        user = password_reset.user

        if request.method == "POST":
            form = SetPasswordForm(request.POST)

            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()

                password_reset.is_used = True
                password_reset.save()

                RateLimit.objects.filter(email=user.email, action='password_reset').delete()

                messages.success(request, "Your password has been reset successfully! You can now log in.")
                return redirect("accounts:login")
        else:
            form = SetPasswordForm()

        return render(request, "accounts/password_reset_confirm.html", {
            "form": form,
            "validlink": True,
            "email": user.email
        })

    except PasswordReset.DoesNotExist:
        messages.error(request, "Invalid password reset link.")
        return redirect("password_reset_request")


@login_required
def password_change_view(request):
    """Allow logged-in users to change their password"""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            messages.success(request, "Your password was successfully changed!")
            return redirect("accounts:profile")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "accounts/password_change.html", {"form": form})

from ..models import PasswordSetup
from ..utils import send_password_setup_email

def password_setup_request_view(request):
    """Request password setup email for social auth users"""
    if not request.user.is_authenticated:
        messages.error(request, "Please log in first.")
        return redirect('accounts:login')

    # Check if user already has a password
    if request.user.has_usable_password():
        messages.info(request, "You already have a password set. You can change it in your profile.")
        return redirect('accounts:profile')

    if request.method == "POST":
        # Check rate limit
        is_allowed, block_info = RateLimit.check_rate_limit(request.user.email, 'password_setup')

        if not is_allowed:
            return render_rate_limit_page(request, 'password_setup', block_info)

        try:
            # Check for existing valid token
            existing_setup = PasswordSetup.objects.filter(
                user=request.user,
                is_used=False
            ).first()

            if existing_setup and existing_setup.is_valid():
                token = existing_setup.token
                logger.info(f"Reusing existing valid password setup token for {request.user.email}")
            else:
                if existing_setup:
                    existing_setup.is_used = True
                    existing_setup.save()

                password_setup = PasswordSetup.objects.create(user=request.user)
                token = password_setup.token
                logger.info(f"Created new password setup token for {request.user.email}")

            try:
                send_password_setup_email(request.user, password_setup)
                RateLimit.objects.filter(email=request.user.email, action='password_setup').delete()

                messages.success(
                    request,
                    "A password setup link has been sent to your email. Please check your inbox."
                )
                return redirect('accounts:profile')

            except Exception as e:
                logger.error(f"Failed to send password setup email: {str(e)}")
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=request.user.email,
                    action='password_setup'
                )
                rate_limit.increment_attempt()

                messages.error(
                    request,
                    "There was an error sending the setup email. Please try again."
                )
                return redirect('accounts:password_setup_request')

        except Exception as e:
            logger.error(f"Error in password setup request: {str(e)}", exc_info=True)
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('accounts:password_setup_request')

    return render(request, "accounts/password_setup_request.html")


def password_setup_confirm_view(request, token):
    """Confirm password setup and set new password"""
    try:
        password_setup = PasswordSetup.objects.get(token=token, is_used=False)

        if not password_setup.is_valid():
            messages.error(request, "The password setup link has expired. Please request a new one.")
            return redirect("accounts:password_setup_request")

        user = password_setup.user

        if request.method == "POST":
            form = SetPasswordForm(request.POST)

            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()

                password_setup.is_used = True
                password_setup.save()

                # Log the user in - specify the backend explicitly
                from django.contrib.auth import login
                login(request, user, backend='accounts.backends.EmailAuthBackend')

                messages.success(request, "Your password has been set successfully! You can now log in with your password.")
                return redirect("dashboard")
        else:
            form = SetPasswordForm()

        return render(request, "accounts/password_setup_confirm.html", {
            "form": form,
            "validlink": True,
            "email": user.email
        })

    except PasswordSetup.DoesNotExist:
        messages.error(request, "Invalid password setup link.")
        return redirect("accounts:password_setup_request")


# ============================================================================
# AJAX ENDPOINTS
# ============================================================================

@csrf_exempt
def check_username(request):
    """Check username availability"""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'available': not exists, 'username': username})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def check_email(request):
    """Check email availability"""
    if request.method == 'POST':
        email = request.POST.get('email', '')
        exists = User.objects.filter(email__iexact=email).exists()
        return JsonResponse({'available': not exists, 'email': email})
    return JsonResponse({'error': 'Invalid request'}, status=400)