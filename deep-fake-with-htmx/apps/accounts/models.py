# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import TimeStampedModel
from django.core.validators import RegexValidator
import os


class UserProfile(TimeStampedModel):
    """Extended user profile with additional fields"""

    NOTIFICATION_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notifications'),
        ('none', 'No Notifications'),
    ]

    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone_number = models.CharField(
        max_length=17,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # Preferences
    email_notifications = models.BooleanField(default=True)
    notification_type = models.CharField(
        max_length=10,
        choices=NOTIFICATION_CHOICES,
        default='email'
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='light'
    )
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')

    # Privacy settings
    profile_public = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    # Statistics (read-only, updated by signals)
    total_uploads = models.PositiveIntegerField(default=0)
    total_scans = models.PositiveIntegerField(default=0)
    account_verified = models.BooleanField(default=False)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        """Return full name or username if names not available"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username

    def get_avatar_url(self):
        """Return avatar URL or default avatar"""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.png'

    def delete_avatar(self):
        """Delete avatar file from storage"""
        if self.avatar:
            if os.path.isfile(self.avatar.path):
                os.remove(self.avatar.path)


class EmailVerification(TimeStampedModel):
    """Email verification tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=255, unique=True)
    verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'

    def __str__(self):
        return f"Verification for {self.email}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PasswordResetToken(TimeStampedModel):
    """Password reset tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'

    def __str__(self):
        return f"Reset token for {self.user.username}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class LoginAttempt(TimeStampedModel):
    """Track login attempts for security"""
    ip_address = models.GenericIPAddressField()
    username = models.CharField(max_length=150)
    success = models.BooleanField()
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
        ordering = ['-created_at']

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.username} - {status} from {self.ip_address}"


class UserActivity(TimeStampedModel):
    """Track user activities"""

    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
        ('email_change', 'Email Change'),
        ('upload', 'File Upload'),
        ('scan', 'Deepfake Scan'),
        ('download', 'File Download'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"


# Signal handlers
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

