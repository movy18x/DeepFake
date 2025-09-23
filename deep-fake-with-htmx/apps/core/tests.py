# core/tests/__init__.py
# Empty file

# core/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import TimeStampedModel, UserActivityModel, FileUploadModel
import uuid


class TestModel(TimeStampedModel):
    """Test model for TimeStampedModel"""
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'core'


class TestUserActivityModel(UserActivityModel):
    """Test model for UserActivityModel"""
    title = models.CharField(max_length=100)

    class Meta:
        app_label = 'core'


class TimeStampedModelTest(TestCase):

    def test_id_generation(self):
        """Test that UUID is generated automatically"""
        instance = TestModel.objects.create(name="Test")
        self.assertIsInstance(instance.id, uuid.UUID)

    def test_timestamps(self):
        """Test that created_at and updated_at are set correctly"""
        before_create = timezone.now()
        instance = TestModel.objects.create(name="Test")
        after_create = timezone.now()

        self.assertGreaterEqual(instance.created_at, before_create)
        self.assertLessEqual(instance.created_at, after_create)
        self.assertEqual(instance.created_at, instance.updated_at)

        # Test update
        original_created = instance.created_at
        original_updated = instance.updated_at

        # Small delay to ensure different timestamp
        import time
        time.sleep(0.01)

        instance.name = "Updated"
        instance.save()

        instance.refresh_from_db()
        self.assertEqual(instance.created_at, original_created)
        self.assertGreater(instance.updated_at, original_updated)


class UserActivityModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def test_user_tracking(self):
        """Test that user fields are set correctly"""
        instance = TestUserActivityModel.objects.create(
            title="Test",
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(instance.created_by, self.user)
        self.assertEqual(instance.updated_by, self.user)


# core/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import JsonResponse
import json


class CoreViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def test_home_view(self):
        """Test home page loads correctly"""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deepfake Detection')

    def test_dashboard_view_requires_login(self):
        """Test dashboard requires authentication"""
        response = self.client.get(reverse('core:dashboard'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('core:dashboard')}")

    def test_dashboard_view_authenticated(self):
        """Test dashboard loads for authenticated users"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get(reverse('core:health_check'))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)


# core/tests/test_utils.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.utils import (
    generate_file_hash,
    get_file_info,
    is_valid_media_file,
    format_file_size,
    cleanup_temp_files
)
import os
import tempfile


class CoreUtilsTest(TestCase):

    def test_generate_file_hash(self):
        """Test file hash generation"""
        content = b"Test file content"
        file = SimpleUploadedFile("test.txt", content)

        hash1 = generate_file_hash(file)
        file.seek(0)  # Reset file pointer
        hash2 = generate_file_hash(file)

        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 produces 64-char hex string

    def test_get_file_info(self):
        """Test file information extraction"""
        content = b"Test file content"
        file = SimpleUploadedFile("test.jpg", content, content_type="image/jpeg")

        name, size, content_type = get_file_info(file)

        self.assertEqual(name, "test.jpg")
        self.assertEqual(size, len(content))
        self.assertEqual(content_type, "image/jpeg")

    def test_is_valid_media_file(self):
        """Test media file validation"""
        # Valid files
        jpg_file = SimpleUploadedFile("test.jpg", b"content", content_type="image/jpeg")
        mp4_file = SimpleUploadedFile("test.mp4", b"content", content_type="video/mp4")

        self.assertTrue(is_valid_media_file(jpg_file))
        self.assertTrue(is_valid_media_file(mp4_file))

        # Invalid file
        txt_file = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        self.assertFalse(is_valid_media_file(txt_file))

    def test_format_file_size(self):
        """Test file size formatting"""
        self.assertEqual(format_file_size(0), "0B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 1024), "1.0 GB")


# core/tests/test_forms.py
from django.test import TestCase
from core.forms import BaseForm
from django import forms


class TestForm(BaseForm):
    """Test form extending BaseForm"""
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    category = forms.ChoiceField(choices=[('1', 'Option 1'), ('2', 'Option 2')])


class BaseFormTest(TestCase):

    def test_form_widget_classes(self):
        """Test that BaseForm adds appropriate CSS classes"""
        form = TestForm()

        # Check that form-control class is added to text input
        self.assertIn('form-control', form.fields['name'].widget.attrs['class'])

        # Check that form-control class is added to email input
        self.assertIn('form-control', form.fields['email'].widget.attrs['class'])

        # Check that form-control class is added to textarea
        self.assertIn('form-control', form.fields['message'].widget.attrs['class'])

        # Check that form-select class is added to select
        self.assertIn('form-select', form.fields['category'].widget.attrs['class'])

    def test_form_alpine_attributes(self):
        """Test that Alpine.js x-model attributes are added"""
        form = TestForm()

        # Check that x-model attributes are added
        self.assertIn('x-model', form.fields['name'].widget.attrs)
        self.assertEqual(form.fields['name'].widget.attrs['x-model'], 'name')


# core/tests/test_mixins.py
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from core.mixins import AjaxResponseMixin, JSONResponseMixin
from django.views.generic import View


class TestAjaxView(AjaxResponseMixin, View):
    template_name = 'test.html'
    htmx_template_name = 'test_htmx.html'

    def get(self, request, *args, **kwargs):
        return JsonResponse({'is_htmx': self.is_htmx})


class TestJSONView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        context = {'message': 'Hello, World!'}
        return self.render_to_json_response(context)


class MixinsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_ajax_response_mixin_regular_request(self):
        """Test AjaxResponseMixin with regular request"""
        request = self.factory.get('/')
        view = TestAjaxView()
        response = view.dispatch(request)

        data = response.json()
        self.assertFalse(data['is_htmx'])

    def test_ajax_response_mixin_htmx_request(self):
        """Test AjaxResponseMixin with HTMX request"""
        request = self.factory.get('/', HTTP_HX_REQUEST='true')
        view = TestAjaxView()
        response = view.dispatch(request)

        data = response.json()
        self.assertTrue(data['is_htmx'])

    def test_json_response_mixin(self):
        """Test JSONResponseMixin"""
        request = self.factory.get('/')
        view = TestJSONView()
        response = view.dispatch(request)

        self.assertIsInstance(response, JsonResponse)
        data = response.json()
        self.assertEqual(data['message'], 'Hello, World!')


# core/tests/test_management_commands.py
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from io import StringIO


class ManagementCommandTest(TestCase):

    def test_create_test_data_command(self):
        """Test create_test_data management command"""
        out = StringIO()
        call_command('create_test_data', '--users=2', stdout=out)

        # Check that users were created
        self.assertEqual(User.objects.filter(username__startswith='testuser').count(), 2)
        self.assertTrue(User.objects.filter(username='admin').exists())

        # Check command output
        output = out.getvalue()
        self.assertIn('Created user: testuser1', output)
        self.assertIn('Created user: testuser2', output)

    def test_system_health_command(self):
        """Test system_health management command"""
        out = StringIO()
        call_command('system_health', stdout=out)

        output = out.getvalue()
        self.assertIn('System Health Check', output)
        self.assertIn('Database:', output)
        self.assertIn('Cache:', output)

    def test_cleanup_temp_files_command(self):
        """Test cleanup_temp_files management command"""
        out = StringIO()
        call_command('cleanup_temp_files', '--dry-run', stdout=out)

        output = out.getvalue()
        self.assertIn('Looking for temporary files', output)