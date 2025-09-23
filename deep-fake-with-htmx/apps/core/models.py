# core/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating
    'created_at' and 'updated_at' fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserActivityModel(TimeStampedModel):
    """
    Abstract base class that adds user tracking fields
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated'
    )

    class Meta:
        abstract = True


class FileUploadModel(TimeStampedModel):
    """
    Abstract base class for file uploads with common fields
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        abstract = True


# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class BaseView(TemplateView):
    """Base view with common functionality"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = getattr(self, 'page_title', 'Deepfake Detection')
        context['active_nav'] = getattr(self, 'active_nav', '')
        return context


class DashboardView(LoginRequiredMixin, BaseView):
    template_name = 'core/dashboard.html'
    page_title = 'Dashboard'
    active_nav = 'dashboard'


class HomeView(BaseView):
    template_name = 'core/home.html'
    page_title = 'Deepfake Detection - Home'
    active_nav = 'home'


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({'status': 'healthy', 'timestamp': timezone.now()})


# core/utils.py
import os
import hashlib
import mimetypes
from django.core.files.storage import default_storage
from django.conf import settings
from typing import Optional, Tuple


def generate_file_hash(file) -> str:
    """Generate SHA-256 hash for uploaded file"""
    hash_sha256 = hashlib.sha256()
    for chunk in file.chunks():
        hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_file_info(file) -> Tuple[str, int, str]:
    """Extract file information"""
    original_name = file.name
    file_size = file.size
    content_type = mimetypes.guess_type(original_name)[0] or 'application/octet-stream'
    return original_name, file_size, content_type


def is_valid_media_file(file) -> bool:
    """Check if uploaded file is a valid media file"""
    allowed_types = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/avi', 'video/mov', 'video/wmv'
    ]
    content_type = mimetypes.guess_type(file.name)[0]
    return content_type in allowed_types


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def cleanup_temp_files(file_paths: list):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        except Exception as e:
            # Log the error but don't raise it
            import logging
            logging.warning(f"Failed to delete temporary file {file_path}: {e}")


# core/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class AjaxResponseMixin:
    """Mixin for handling AJAX requests"""

    def dispatch(self, request, *args, **kwargs):
        if request.headers.get('HX-Request'):
            # HTMX request
            self.is_htmx = True
        else:
            self.is_htmx = False
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.is_htmx and hasattr(self, 'htmx_template_name'):
            return [self.htmx_template_name]
        return super().get_template_names()


class JSONResponseMixin:
    """Mixin to add JSON support to a view"""

    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(context, **response_kwargs)


# core/forms.py
from django import forms


class BaseForm(forms.Form):
    """Base form with common styling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add common CSS classes for styling
        for field in self.fields.values():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'x-model': f'{field.label.lower().replace(" ", "_")}'
                })
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'x-model': f'{field.label.lower().replace(" ", "_")}'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 3,
                    'x-model': f'{field.label.lower().replace(" ", "_")}'
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select',
                    'x-model': f'{field.label.lower().replace(" ", "_")}'
                })


# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('health/', views.health_check, name='health_check'),
]

# core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'

# core/__init__.py
# Empty file to make Python treat the directory as a package