
# accounts/managers.py
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Custom user manager with additional methods"""

    def create_user_with_profile(self, username, email, password=None, **extra_fields):
        """Create user with profile in single transaction"""
        from django.db import transaction

        with transaction.atomic():
            user = self.create_user(
                username=username,
                email=email,
                password=password,
                **extra_fields
            )
            # Profile is created automatically via signal
            return user

    def get_by_email_or_username(self, identifier):
        """Get user by email or username"""
        from django.db.models import Q
        return self.get(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        )

