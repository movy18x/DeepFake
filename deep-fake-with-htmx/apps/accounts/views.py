
# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from apps.core.mixins import AjaxResponseMixin
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    UserProfileForm,
    UserPreferencesForm,
    AvatarUploadForm,
    PasswordResetRequestForm,
    PasswordResetForm
)
from .models import UserProfile, EmailVerification, PasswordResetToken, LoginAttempt
from .utils import (
    send_verification_email,
    send_password_reset_email,
    log_user_activity,
    get_client_ip,
    check_rate_limit
)
import json


class RegisterView(AjaxResponseMixin, CreateView):
    """User registration view"""
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    htmx_template_name = 'accounts/partials/register_form.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        # Check rate limiting
        ip_address = get_client_ip(self.request)
        if check_rate_limit(ip_address, max_attempts=3, time_window=3600):
            messages.error(self.request, 'Too many registration attempts. Please try again later.')
            return self.form_invalid(form)

        with transaction.atomic():
            user = form.save()

            # Send verification email
            try:
                send_verification_email(user)
                messages.success(
                    self.request,
                    'Account created successfully! Please check your email to verify your account.'
                )
            except Exception as e:
                messages.warning(
                    self.request,
                    'Account created but we could not send verification email. You can request it later.'
                )

            # Log activity
            log_user_activity(
                user,
                'registration',
                'User registered successfully',
                self.request
            )

        if self.is_htmx:
            return JsonResponse({
                'success': True,
                'message': 'Registration successful! Please check your email.',
                'redirect': str(self.success_url)
            })

        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.is_htmx:
            return render(self.request, self.htmx_template_name, {'form': form})
        return super().form_invalid(form)


class LoginView(AjaxResponseMixin, TemplateView):
    """User login view"""
    template_name = 'accounts/login.html'
    htmx_template_name = 'accounts/partials/login_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomAuthenticationForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CustomAuthenticationForm(data=request.POST)
        ip_address = get_client_ip(request)

        # Check rate limiting
        if check_rate_limit(ip_address):
            messages.error(request, 'Too many failed login attempts. Please try again later.')
            return self.render_form_response(form)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Try to authenticate with username or email
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Log successful attempt
                LoginAttempt.objects.create(
                    ip_address=ip_address,
                    username=username,
                    success=True,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                login(request, user)

                # Set session expiry
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks

                # Log activity
                log_user_activity(user, 'login', 'User logged in', request)

                # Get next URL
                next_url = request.GET.get('next', reverse_lazy('core:dashboard'))

                if self.is_htmx:
                    return JsonResponse({
                        'success': True,
                        'message': f'Welcome back, {user.get_full_name() or user.username}!',
                        'redirect': str(next_url)
                    })

                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect(next_url)
            else:
                # Log failed attempt
                LoginAttempt.objects.create(
                    ip_address=ip_address,
                    username=username,
                    success=False,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                form.add_error(None, 'Invalid username/email or password.')

        return self.render_form_response(form)

    def render_form_response(self, form):
        if self.is_htmx:
            return render(self.request, self.htmx_template_name, {'form': form})
        return render(self.request, self.template_name, {'form': form})


@login_required
def logout_view(request):
    """User logout view"""
    user = request.user
    log_user_activity(user, 'logout', 'User logged out', request)
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


class ProfileView(LoginRequiredMixin, AjaxResponseMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'
    htmx_template_name = 'accounts/partials/profile_content.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update({
            'profile': user.userprofile,
            'user_form': UserProfileForm(instance=user),
            'preferences_form': UserPreferencesForm(instance=user.userprofile),
            'avatar_form': AvatarUploadForm(),
            'recent_activities': user.useractivity_set.all()[:10]
        })
        return context


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """Update user profile via HTMX"""
    user = request.user
    form = UserProfileForm(request.POST, instance=user)

    if form.is_valid():
        with transaction.atomic():
            # Update User model fields
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()

            # Update UserProfile model fields
            profile = user.userprofile
            profile.bio = form.cleaned_data['bio']
            profile.phone_number = form.cleaned_data['phone_number']
            profile.website = form.cleaned_data['website']
            profile.location = form.cleaned_data['location']
            profile.birth_date = form.cleaned_data['birth_date']
            profile.save()

            log_user_activity(user, 'profile_update', 'Profile updated', request)

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully!'
        })

    return JsonResponse({
        'success': False,
        'errors': form.errors
    })


@login_required
@require_http_methods(["POST"])
def update_preferences(request):
    """Update user preferences via HTMX"""
    user = request.user
    form = UserPreferencesForm(request.POST, instance=user.userprofile)

    if form.is_valid():
        profile = form.save(commit=False)
        profile.user = user
        profile.save()

        log_user_activity(user, 'profile_update', 'Preferences updated', request)

        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully!'
        })

    return JsonResponse({
        'success': False,
        'errors': form.errors
    })


@login_required
@require_http_methods(["POST"])
def upload_avatar(request):
    """Upload user avatar via HTMX"""
    user = request.user
    form = AvatarUploadForm(request.POST, request.FILES)

    if form.is_valid():
        profile = user.userprofile

        # Delete old avatar if exists
        profile.delete_avatar()

        # Save new avatar
        profile.avatar = form.cleaned_data['avatar']
        profile.save()

        log_user_activity(user, 'profile_update', 'Avatar updated', request)

        return JsonResponse({
            'success': True,
            'message': 'Avatar updated successfully!',
            'avatar_url': profile.get_avatar_url()
        })

    return JsonResponse({
        'success': False,
        'errors': form.errors
    })


@login_required
@require_http_methods(["POST"])
def delete_avatar(request):
    """Delete user avatar via HTMX"""
    user = request.user
    profile = user.userprofile

    profile.delete_avatar()
    profile.avatar = None
    profile.save()

    log_user_activity(user, 'profile_update', 'Avatar deleted', request)

    return JsonResponse({
        'success': True,
        'message': 'Avatar deleted successfully!',
        'avatar_url': profile.get_avatar_url()
    })


def verify_email(request, token):
    """Email verification view"""
    try:
        verification = get_object_or_404(
            EmailVerification,
            token=token,
            verified=False
        )

        if verification.is_expired():
            messages.error(request, 'Verification link has expired. Please request a new one.')
        else:
            verification.verified = True
            verification.save()

            # Update user profile
            profile = verification.user.userprofile
            profile.account_verified = True
            profile.save()

            log_user_activity(
                verification.user,
                'email_verification',
                'Email verified successfully',
                request
            )

            messages.success(request, 'Email verified successfully! Your account is now active.')

    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification link.')

    return redirect('accounts:login')


class PasswordResetRequestView(AjaxResponseMixin, TemplateView):
    """Password reset request view"""
    template_name = 'accounts/password_reset_request.html'
    htmx_template_name = 'accounts/partials/password_reset_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PasswordResetRequestForm()
        return context

    def post(self, request, *args, **kwargs):
        form = PasswordResetRequestForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email__iexact=email)

            try:
                send_password_reset_email(user)
                messages.success(
                    request,
                    'Password reset instructions have been sent to your email.'
                )

                if self.is_htmx:
                    return JsonResponse({
                        'success': True,
                        'message': 'Reset instructions sent to your email!'
                    })

                return redirect('accounts:login')

            except Exception as e:
                messages.error(request, 'Failed to send reset email. Please try again.')

        if self.is_htmx:
            return render(request, self.htmx_template_name, {'form': form})

        return render(request, self.template_name, {'form': form})


def password_reset_confirm(request, token):
    """Password reset confirmation view"""
    try:
        reset_token = get_object_or_404(
            PasswordResetToken,
            token=token,
            used=False
        )

        if reset_token.is_expired():
            messages.error(request, 'Reset link has expired. Please request a new one.')
            return redirect('accounts:password_reset_request')

        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                user = reset_token.user
                user.set_password(form.cleaned_data['password1'])
                user.save()

                # Mark token as used
                reset_token.used = True
                reset_token.save()

                log_user_activity(user, 'password_change', 'Password reset via email', request)

                messages.success(request, 'Password reset successfully! You can now log in.')
                return redirect('accounts:login')
        else:
            form = PasswordResetForm()

        return render(request, 'accounts/password_reset_confirm.html', {
            'form': form,
            'token': token
        })

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('accounts:password_reset_request')



# Additional view methods for accounts/views.py (append to existing file)

@login_required
@require_http_methods(["POST"])
def resend_verification(request):
    """Resend email verification"""
    user = request.user

    if user.userprofile.account_verified:
        return JsonResponse({
            'success': False,
            'message': 'Your email is already verified.'
        })

    try:
        send_verification_email(user)
        return JsonResponse({
            'success': True,
            'message': 'Verification email sent successfully!'
        })
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to send verification email. Please try again later.'
        })


@login_required
def change_password(request):
    """Change password modal content"""
    if request.method == 'GET':
        return render(request, 'accounts/partials/change_password_modal.html')

    # Handle password change POST request
    from django.contrib.auth.forms import PasswordChangeForm

    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)  # Keep user logged in

        log_user_activity(user, 'password_change', 'Password changed successfully', request)

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully!'
        })

    return render(request, 'accounts/partials/change_password_modal.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def delete_account(request):
    """Delete user account"""
    user = request.user

    # Log the deletion
    log_user_activity(user, 'account_deletion', 'Account deleted by user', request)

    # Delete the user (this will also delete related data via CASCADE)
    user.delete()

    messages.success(request, 'Your account has been deleted successfully.')
    return JsonResponse({
        'success': True,
        'message': 'Account deleted successfully.',
        'redirect': '/'
    })


@require_http_methods(["GET"])
def check_username_availability(request):
    """Check if username is available"""
    username = request.GET.get('username', '').strip()

    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})

    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters'})

    available = not User.objects.filter(username__iexact=username).exists()

    return JsonResponse({
        'available': available,
        'message': 'Username is available' if available else 'Username is already taken'
    })


@require_http_methods(["GET"])
def check_email_availability(request):
    """Check if email is available"""
    email = request.GET.get('email', '').strip()

    if not email:
        return JsonResponse({'available': False, 'message': 'Email is required'})

    available = not User.objects.filter(email__iexact=email).exists()

    return JsonResponse({
        'available': available,
        'message': 'Email is available' if available else 'Email is already registered'
    })

