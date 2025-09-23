
# accounts/utils.py
import secrets
import string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerification, PasswordResetToken


def generate_token(length=32):
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_verification_email(user, email=None):
    """Send email verification link"""
    if email is None:
        email = user.email

    token = generate_token()
    expires_at = timezone.now() + timedelta(hours=24)

    verification = EmailVerification.objects.create(
        user=user,
        email=email,
        token=token,
        expires_at=expires_at
    )

    subject = 'Verify your email address'
    message = render_to_string('accounts/emails/verify_email.html', {
        'user': user,
        'token': token,
        'site_name': getattr(settings, 'SITE_NAME', 'Deepfake Detection'),
    })

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return verification


def send_password_reset_email(user):
    """Send password reset link"""
    token = generate_token()
    expires_at = timezone.now() + timedelta(hours=2)

    reset_token = PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )

    subject = 'Reset your password'
    message = render_to_string('accounts/emails/password_reset.html', {
        'user': user,
        'token': token,
        'site_name': getattr(settings, 'SITE_NAME', 'Deepfake Detection'),
    })

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return reset_token


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_activity(user, activity_type, description='', request=None, extra_data=None):
    """Log user activity"""
    from .models import UserActivity

    ip_address = '127.0.0.1'
    user_agent = ''

    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data or {}
    )


def is_safe_url(url, allowed_hosts=None, require_https=False):
    """Check if URL is safe for redirect"""
    from urllib.parse import urlparse

    if not url:
        return False

    parsed = urlparse(url)

    # Check for allowed hosts
    if allowed_hosts and parsed.netloc and parsed.netloc not in allowed_hosts:
        return False

    # Check for HTTPS requirement
    if require_https and parsed.scheme != 'https':
        return False

    # Don't allow javascript: or data: URLs
    if parsed.scheme in ('javascript', 'data'):
        return False

    return True


def check_rate_limit(ip_address, max_attempts=5, time_window=300):
    """Check if IP address has exceeded rate limit"""
    from .models import LoginAttempt
    from django.utils import timezone

    time_threshold = timezone.now() - timedelta(seconds=time_window)

    recent_attempts = LoginAttempt.objects.filter(
        ip_address=ip_address,
        success=False,
        created_at__gte=time_threshold
    ).count()

    return recent_attempts >= max_attempts