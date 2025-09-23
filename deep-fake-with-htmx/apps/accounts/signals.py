
# accounts/signals.py
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import UserProfile, UserActivity
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when user is saved"""
    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"Created profile for user: {instance.username}")
    else:
        if hasattr(instance, 'userprofile'):
            instance.userprofile.save()


@receiver(pre_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """Clean up user data before deletion"""
    # Delete avatar file if exists
    if hasattr(instance, 'userprofile') and instance.userprofile.avatar:
        instance.userprofile.delete_avatar()

    # Clear user-related cache
    cache.delete_pattern(f"user_{instance.id}_*")

    logger.info(f"Cleaned up data for user: {instance.username}")


@receiver(post_save, sender=UserActivity)
def update_user_last_active(sender, instance, created, **kwargs):
    """Update user's last active timestamp when activity is logged"""
    if created and instance.user:
        try:
            profile = instance.user.userprofile
            profile.last_active = instance.created_at
            profile.save(update_fields=['last_active'])
        except UserProfile.DoesNotExist:
            pass


