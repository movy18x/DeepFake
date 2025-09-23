# accounts/tests/__init__.py
# Empty file

# accounts/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from accounts.models import (
    UserProfile,
    EmailVerification,
    PasswordResetToken,
    LoginAttempt,
    UserActivity
)


class UserProfileModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_profile_created_automatically(self):
        """Test that UserProfile is created automatically when User is created"""
        self.assertTrue(hasattr(self.user, 'userprofile'))
        self.assertIsInstance(self.user.userprofile, UserProfile)

    def test_get_full_name(self):
        """Test get_full_name method"""
        # Test with first and last name
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()

        self.assertEqual(self.user.userprofile.get_full_name(), 'John Doe')

        # Test with username fallback
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()

        self.assertEqual(self.user.userprofile.get_full_name(), 'testuser')

    def test_get_avatar_url(self):
        """Test get_avatar_url method"""
        profile = self.user.userprofile

        # Test default avatar URL
        self.assertEqual(profile.get_avatar_url(), '/static/images/default-avatar.png')

    def test_phone_number_validation(self):
        """Test phone number validation"""
        profile = self.user.userprofile

        # Valid phone numbers
        valid_numbers = ['+1234567890', '1234567890', '+123456789012345']

        for number in valid_numbers:
            profile.phone_number = number
            profile.full_clean()  # Should not raise ValidationError

        # Invalid phone numbers
        profile.phone_number = '123'  # Too short
        with self.assertRaises(ValidationError):
            profile.full_clean()


class EmailVerificationModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_is_expired_method(self):
        """Test is_expired method"""
        # Create expired verification
        expired_verification = EmailVerification.objects.create(
            user=self.user,
            email='test@example.com',
            token='expired_token',
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertTrue(expired_verification.is_expired())

        # Create active verification
        active_verification = EmailVerification.objects.create(
            user=self.user,
            email='test@example.com',
            token='active_token',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        self.assertFalse(active_verification.is_expired())


class PasswordResetTokenModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_is_expired_method(self):
        """Test is_expired method"""
        # Create expired token
        expired_token = PasswordResetToken.objects.create(
            user=self.user,
            token='expired_token',
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertTrue(expired_token.is_expired())

        # Create active token
        active_token = PasswordResetToken.objects.create(
            user=self.user,
            token='active_token',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        self.assertFalse(active_token.is_expired())


class UserActivityModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_activity_creation(self):
        """Test UserActivity creation"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='User logged in',
            ip_address='127.0.0.1'
        )

        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(str(activity), f"{self.user.username} - User Login")


# accounts/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from accounts.models import EmailVerification, PasswordResetToken
import json


class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')

    def test_register_get_request(self):
        """Test GET request to register view"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')

    def test_register_post_valid_data(self):
        """Test POST request with valid registration data"""
        data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': True
        }

        response = self.client.post(self.register_url, data)

        # Check user was created
        self.assertTrue(User.objects.filter(username='testuser').exists())

        # Check redirect
        self.assertRedirects(response, reverse('accounts:login'))

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your email', mail.outbox[0].subject)

    def test_register_post_duplicate_username(self):
        """Test registration with duplicate username"""
        # Create existing user
        User.objects.create_user('testuser', 'existing@example.com', 'pass123')

        data = {
            'username': 'testuser',  # Duplicate username
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': True
        }

        response = self.client.post(self.register_url, data)

        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user with that username already exists')

    def test_register_post_duplicate_email(self):
        """Test registration with duplicate email"""
        # Create existing user
        User.objects.create_user('existinguser', 'test@example.com', 'pass123')

        data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',  # Duplicate email
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': True
        }

        response = self.client.post(self.register_url, data)

        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user with this email address already exists')


class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_get_request(self):
        """Test GET request to login view"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back')

    def test_login_with_username(self):
        """Test login with username"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, data)

        # Should redirect to dashboard
        self.assertRedirects(response, reverse('core:dashboard'))

        # User should be logged in
        user = User.objects.get(username='testuser')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_login_with_email(self):
        """Test login with email"""
        data = {
            'username': 'test@example.com',  # Using email instead of username
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, data)

        # Should redirect to dashboard
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.login_url, data)

        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username/email or password')


class ProfileViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile_url = reverse('accounts:profile')

    def test_profile_requires_login(self):
        """Test that profile view requires login"""
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f'/accounts/login/?next={self.profile_url}')

    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)


class EmailVerificationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_email_verification_valid_token(self):
        """Test email verification with valid token"""
        # Create verification token
        verification = EmailVerification.objects.create(
            user=self.user,
            email='test@example.com',
            token='valid_token',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        url = reverse('accounts:verify_email', kwargs={'token': 'valid_token'})
        response = self.client.get(url)

        # Should redirect to login
        self.assertRedirects(response, reverse('accounts:login'))

        # Verification should be marked as verified
        verification.refresh_from_db()
        self.assertTrue(verification.verified)

        # User profile should be verified
        self.user.userprofile.refresh_from_db()
        self.assertTrue(self.user.userprofile.account_verified)

    def test_email_verification_expired_token(self):
        """Test email verification with expired token"""
        # Create expired verification token
        EmailVerification.objects.create(
            user=self.user,
            email='test@example.com',
            token='expired_token',
            expires_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('accounts:verify_email', kwargs={'token': 'expired_token'})
        response = self.client.get(url)

        # Should redirect to login with error message
        self.assertRedirects(response, reverse('accounts:login'))

    def test_email_verification_invalid_token(self):
        """Test email verification with invalid token"""
        url = reverse('accounts:verify_email', kwargs={'token': 'invalid_token'})
        response = self.client.get(url)

        # Should redirect to login with error message
        self.assertRedirects(response, reverse('accounts:login'))


class PasswordResetTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.reset_request_url = reverse('accounts:password_reset_request')

    def test_password_reset_request_valid_email(self):
        """Test password reset request with valid email"""
        data = {'email': 'test@example.com'}

        response = self.client.post(self.reset_request_url, data)

        # Should redirect to login
        self.assertRedirects(response, reverse('accounts:login'))

        # Should create reset token
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

        # Should send email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset your password', mail.outbox[0].subject)

    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email"""
        data = {'email': 'nonexistent@example.com'}

        response = self.client.post(self.reset_request_url, data)

        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account found with this email address')

    def test_password_reset_confirm_valid_token(self):
        """Test password reset confirmation with valid token"""
        # Create reset token
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token='valid_reset_token',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        url = reverse('accounts:password_reset_confirm', kwargs={'token': 'valid_reset_token'})

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New password')

        # Test POST request
        data = {
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        }

        response = self.client.post(url, data)

        # Should redirect to login
        self.assertRedirects(response, reverse('accounts:login'))

        # Token should be marked as used
        reset_token.refresh_from_db()
        self.assertTrue(reset_token.used)

        # User password should be updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123!'))


# accounts/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth.models import User
from accounts.forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    UserProfileForm,
    AvatarUploadForm
)
from django.core.files.uploadedfile import SimpleUploadedFile


class CustomUserCreationFormTest(TestCase):

    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': True
        }

        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_duplicate_email(self):
        """Test form with duplicate email"""
        # Create existing user
        User.objects.create_user('existinguser', 'test@example.com', 'pass123')

        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',  # Duplicate email
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': True
        }

        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch(self):
        """Test form with password mismatch"""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'DifferentPass123!',
            'terms_accepted': True
        }

        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_terms_not_accepted(self):
        """Test form without accepting terms"""
        form_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_accepted': False  # Not accepted
        }

        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('terms_accepted', form.errors)


class AvatarUploadFormTest(TestCase):

    def test_valid_image_upload(self):
        """Test form with valid image"""
        # Create a small test image
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
        uploaded_file = SimpleUploadedFile(
            "test.gif",
            image_content,
            content_type="image/gif"
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        self.assertTrue(form.is_valid())

    def test_invalid_file_type(self):
        """Test form with invalid file type"""
        text_file = SimpleUploadedFile(
            "test.txt",
            b"file content",
            content_type="text/plain"
        )

        form = AvatarUploadForm(files={'avatar': text_file})
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)


# accounts/tests/test_utils.py
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core import mail
from accounts.utils import (
    generate_token,
    send_verification_email,
    send_password_reset_email,
    get_client_ip,
    log_user_activity,
    check_rate_limit
)
from accounts.models import EmailVerification, PasswordResetToken, UserActivity, LoginAttempt


class UtilsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_generate_token(self):
        """Test token generation"""
        token1 = generate_token()
        token2 = generate_token()

        # Tokens should be different
        self.assertNotEqual(token1, token2)

        # Default length should be 32
        self.assertEqual(len(token1), 32)

        # Custom length
        custom_token = generate_token(16)
        self.assertEqual(len(custom_token), 16)

    def test_send_verification_email(self):
        """Test sending verification email"""
        verification = send_verification_email(self.user)

        # Should create EmailVerification record
        self.assertIsInstance(verification, EmailVerification)
        self.assertEqual(verification.user, self.user)
        self.assertEqual(verification.email, self.user.email)

        # Should send email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your email', mail.outbox[0].subject)

    def test_send_password_reset_email(self):
        """Test sending password reset email"""
        reset_token = send_password_reset_email(self.user)

        # Should create PasswordResetToken record
        self.assertIsInstance(reset_token, PasswordResetToken)
        self.assertEqual(reset_token.user, self.user)

        # Should send email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset your password', mail.outbox[0].subject)

    def test_get_client_ip(self):
        """Test getting client IP address"""
        # Test with X-Forwarded-For header
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.1, 10.0.0.1')
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

        # Test with REMOTE_ADDR
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        ip = get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')

    def test_log_user_activity(self):
        """Test logging user activity"""
        request = self.factory.get('/')

        log_user_activity(
            self.user,
            'login',
            'User logged in successfully',
            request,
            {'test': 'data'}
        )

        # Should create UserActivity record
        activity = UserActivity.objects.get(user=self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.description, 'User logged in successfully')
        self.assertEqual(activity.extra_data, {'test': 'data'})

    def test_check_rate_limit(self):
        """Test rate limiting functionality"""
        ip_address = '127.0.0.1'

        # Create failed login attempts
        for i in range(3):
            LoginAttempt.objects.create(
                ip_address=ip_address,
                username='testuser',
                success=False
            )

        # Should not be rate limited yet (default max is 5)
        self.assertFalse(check_rate_limit(ip_address))

        # Add more attempts
        for i in range(3):
            LoginAttempt.objects.create(
                ip_address=ip_address,
                username='testuser',
                success=False
            )

        # Should now be rate limited
        self.assertTrue(check_rate_limit(ip_address))