# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import ModelAdmin


class BaseModelAdmin(ModelAdmin):
    """
    Base admin class with common functionality
    """
    list_per_page = 25
    save_on_top = True

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if hasattr(self.model, 'created_at'):
            readonly_fields.extend(['id', 'created_at', 'updated_at'])
        if hasattr(self.model, 'created_by') and obj:
            readonly_fields.extend(['created_by', 'updated_by'])
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            if hasattr(obj, 'created_by'):
                obj.created_by = request.user
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class TimeStampedModelAdmin(BaseModelAdmin):
    """
    Admin class for TimeStampedModel with common date filters
    """
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if 'created_at' not in list_display:
            list_display.append('created_at')
        return list_display


# core/management/__init__.py
# Empty file

# core/management/commands/__init__.py
# Empty file

# core/management/commands/cleanup_temp_files.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up temporary files older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete files older than this many days (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = datetime.now() - timedelta(days=days)

        self.stdout.write(f"Looking for temporary files older than {days} days...")

        temp_dirs = [
            'temp/',
            'uploads/temp/',
            'media/temp/',
        ]

        deleted_count = 0
        total_size = 0

        for temp_dir in temp_dirs:
            if default_storage.exists(temp_dir):
                try:
                    dirs, files = default_storage.listdir(temp_dir)

                    for file_name in files:
                        file_path = os.path.join(temp_dir, file_name)

                        try:
                            # Get file modification time
                            file_stat = default_storage.stat(file_path)
                            file_date = datetime.fromtimestamp(file_stat.st_mtime)

                            if file_date < cutoff_date:
                                file_size = file_stat.st_size

                                if dry_run:
                                    self.stdout.write(f"Would delete: {file_path} ({self.format_bytes(file_size)})")
                                else:
                                    default_storage.delete(file_path)
                                    self.stdout.write(f"Deleted: {file_path} ({self.format_bytes(file_size)})")

                                deleted_count += 1
                                total_size += file_size

                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {e}")

                except Exception as e:
                    logger.error(f"Error accessing directory {temp_dir}: {e}")

        action = "Would delete" if dry_run else "Deleted"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {deleted_count} files, "
                f"freed {self.format_bytes(total_size)} of storage"
            )
        )

    def format_bytes(self, size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# core/management/commands/system_health.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import os
import psutil
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check system health and report issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed health information'
        )

    def handle(self, *args, **options):
        verbose = options['verbose']

        self.stdout.write("=== System Health Check ===\n")

        issues = []

        # Check database connection
        db_status = self.check_database()
        if not db_status:
            issues.append("Database connection failed")

        # Check cache
        cache_status = self.check_cache()
        if not cache_status:
            issues.append("Cache system not working")

        # Check disk space
        disk_issues = self.check_disk_space()
        issues.extend(disk_issues)

        # Check memory usage
        memory_issues = self.check_memory()
        issues.extend(memory_issues)

        # Check required directories
        dir_issues = self.check_directories()
        issues.extend(dir_issues)

        if verbose:
            self.show_detailed_info()

        # Summary
        if issues:
            self.stdout.write(self.style.ERROR("\n⚠️  Issues found:"))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f"  - {issue}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ All systems healthy!"))

    def check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.stdout.write("✅ Database: Connected")
            return True
        except Exception as e:
            self.stdout.write(f"❌ Database: Failed - {e}")
            return False

    def check_cache(self):
        try:
            test_key = 'health_check_test'
            test_value = 'test_value'
            cache.set(test_key, test_value, 10)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)

            if retrieved_value == test_value:
                self.stdout.write("✅ Cache: Working")
                return True
            else:
                self.stdout.write("❌ Cache: Not storing values correctly")
                return False
        except Exception as e:
            self.stdout.write(f"❌ Cache: Failed - {e}")
            return False

    def check_disk_space(self):
        issues = []
        try:
            # Check media directory
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.exists(media_root):
                usage = psutil.disk_usage(media_root)
                free_percent = (usage.free / usage.total) * 100

                if free_percent < 10:
                    issues.append(f"Low disk space in media directory: {free_percent:.1f}% free")

                self.stdout.write(f"✅ Disk Space (Media): {free_percent:.1f}% free")

        except Exception as e:
            issues.append(f"Could not check disk space: {e}")

        return issues

    def check_memory(self):
        issues = []
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent}%")

            self.stdout.write(f"✅ Memory Usage: {memory.percent}%")
        except Exception as e:
            issues.append(f"Could not check memory usage: {e}")

        return issues

    def check_directories(self):
        issues = []
        required_dirs = [
            settings.MEDIA_ROOT,
            os.path.join(settings.MEDIA_ROOT, 'uploads'),
            os.path.join(settings.MEDIA_ROOT, 'temp'),
        ]

        for directory in required_dirs:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    self.stdout.write(f"✅ Created directory: {directory}")
                except Exception as e:
                    issues.append(f"Cannot create required directory {directory}: {e}")
            else:
                self.stdout.write(f"✅ Directory exists: {directory}")

        return issues

    def show_detailed_info(self):
        self.stdout.write("\n=== Detailed System Information ===")

        # System info
        self.stdout.write(f"Python Version: {psutil.version_info}")
        self.stdout.write(f"CPU Count: {psutil.cpu_count()}")

        # Memory details
        memory = psutil.virtual_memory()
        self.stdout.write(f"Memory Total: {self.format_bytes(memory.total)}")
        self.stdout.write(f"Memory Used: {self.format_bytes(memory.used)}")
        self.stdout.write(f"Memory Free: {self.format_bytes(memory.available)}")

        # Disk details
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.exists(media_root):
                usage = psutil.disk_usage(media_root)
                self.stdout.write(f"Disk Total: {self.format_bytes(usage.total)}")
                self.stdout.write(f"Disk Used: {self.format_bytes(usage.used)}")
                self.stdout.write(f"Disk Free: {self.format_bytes(usage.free)}")
        except Exception:
            pass

    def format_bytes(self, size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


# core/management/commands/create_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create test data for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of test users to create (default: 5)'
        )

    def handle(self, *args, **options):
        users_count = options['users']

        self.stdout.write("Creating test data...")

        with transaction.atomic():
            # Create test users
            created_users = []
            for i in range(users_count):
                username = f'testuser{i + 1}'
                email = f'testuser{i + 1}@example.com'

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': f'Test{i + 1}',
                        'last_name': 'User',
                        'is_active': True,
                    }
                )

                if created:
                    user.set_password('testpass123')
                    user.save()
                    created_users.append(user)
                    self.stdout.write(f"Created user: {username}")

        # Create admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write("Created admin user: admin/admin123")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(created_users)} test users"
            )
        )


# core/context_processors.py
from django.conf import settings


def app_context(request):
    """Add common app context to all templates"""
    return {
        'app_name': getattr(settings, 'APP_NAME', 'Deepfake Detection'),
        'app_version': getattr(settings, 'APP_VERSION', '1.0.0'),
        'debug': settings.DEBUG,
    }


# core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_saved(sender, instance, created, **kwargs):
    """Handle user save events"""
    if created:
        logger.info(f"New user created: {instance.username}")
        # Clear user-related cache
        cache.delete_pattern("user_*")
    else:
        logger.info(f"User updated: {instance.username}")


@receiver(post_delete)
def model_deleted(sender, instance, **kwargs):
    """Handle model deletion events"""
    logger.info(f"Deleted {sender.__name__}: {instance}")

    # Clear related cache entries
    cache.delete_pattern(f"{sender._meta.app_label}_*")


# core/middleware.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all requests for debugging"""

    def process_request(self, request):
        request.start_time = time.time()

        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(f"Request: {request.method} {request.path} - User: {request.user.username}")
        else:
            logger.info(f"Request: {request.method} {request.path} - Anonymous")

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(f"Response: {response.status_code} - Duration: {duration:.2f}s")

        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to responses"""

    def process_response(self, request, response):
        # Only add headers if not already present
        if 'X-Content-Type-Options' not in response:
            response['X-Content-Type-Options'] = 'nosniff'

        if 'X-Frame-Options' not in response:
            response['X-Frame-Options'] = 'DENY'

        if 'X-XSS-Protection' not in response:
            response['X-XSS-Protection'] = '1; mode=block'

        return response