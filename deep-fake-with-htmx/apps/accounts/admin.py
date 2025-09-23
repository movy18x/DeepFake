
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from apps.core.admin import TimeStampedModelAdmin
from .models import (
    UserProfile,
    EmailVerification,
    PasswordResetToken,
    LoginAttempt,
    UserActivity
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['total_uploads', 'total_scans', 'last_active']


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined',
                    'get_verification_status')
    list_filter = ('is_active', 'is_staff', 'date_joined', 'userprofile__account_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_verification_status(self, obj):
        if hasattr(obj, 'userprofile'):
            if obj.userprofile.account_verified:
                return format_html('<span style="color: green;">✓ Verified</span>')
            return format_html('<span style="color: orange;">⚠ Unverified</span>')
        return 'No Profile'

    get_verification_status.short_description = 'Email Status'


@admin.register(UserProfile)
class UserProfileAdmin(TimeStampedModelAdmin):
    list_display = ('user', 'get_full_name', 'account_verified', 'total_uploads', 'total_scans', 'last_active')
    list_filter = ('account_verified', 'theme_preference', 'notification_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'bio')
    readonly_fields = ['total_uploads', 'total_scans', 'last_active'] + TimeStampedModelAdmin.readonly_fields

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'avatar', 'phone_number', 'website', 'location', 'birth_date')
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'notification_type', 'theme_preference', 'timezone', 'language')
        }),
        ('Privacy Settings', {
            'fields': ('profile_public', 'show_email', 'show_phone')
        }),
        ('Account Status', {
            'fields': ('account_verified', 'total_uploads', 'total_scans', 'last_active')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = 'Full Name'


@admin.register(EmailVerification)
class EmailVerificationAdmin(TimeStampedModelAdmin):
    list_display = ('email', 'user', 'verified', 'expires_at', 'created_at')
    list_filter = ('verified', 'expires_at', 'created_at')
    search_fields = ('email', 'user__username', 'token')
    readonly_fields = ['token'] + TimeStampedModelAdmin.readonly_fields

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing verification tokens


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(TimeStampedModelAdmin):
    list_display = ('user', 'used', 'expires_at', 'created_at')
    list_filter = ('used', 'expires_at', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ['token'] + TimeStampedModelAdmin.readonly_fields

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing reset tokens


@admin.register(LoginAttempt)
class LoginAttemptAdmin(TimeStampedModelAdmin):
    list_display = ('username', 'ip_address', 'success', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('username', 'ip_address')
    readonly_fields = TimeStampedModelAdmin.readonly_fields

    def has_add_permission(self, request):
        return False  # Don't allow manual creation

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing login attempts


@admin.register(UserActivity)
class UserActivityAdmin(TimeStampedModelAdmin):
    list_display = ('user', 'activity_type', 'ip_address', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'description', 'ip_address')
    readonly_fields = ['extra_data'] + TimeStampedModelAdmin.readonly_fields

    def has_add_permission(self, request):
        return False  # Don't allow manual creation

    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing activities


# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
