# accounts/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from core.forms import BaseForm
from .models import UserProfile
import re


class CustomUserCreationForm(UserCreationForm, BaseForm):
    """Extended user creation form"""


    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'x-model': 'email'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'x-model': 'first_name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
            'x-model': 'last_name'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'x-model': 'terms_accepted'
        }),
        label='I agree to the Terms of Service and Privacy Policy'
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize username field
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'x-model': 'username'
        })

        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password',
            'x-model': 'password1'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'x-model': 'password2'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email.lower()

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Check if username contains only allowed characters
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")

        # Check minimum length
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        return username


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with email support"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'x-model': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'x-model': 'password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'x-model': 'remember_me'
        })
    )


class UserProfileForm(BaseForm):
    """User profile update form"""

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        max_length=500,
        required=False
    )
    phone_number = forms.CharField(max_length=17, required=False)
    website = forms.URLField(required=False)
    location = forms.CharField(max_length=100, required=False)
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    class Meta:
        fields = [
            'first_name', 'last_name', 'email', 'bio', 'phone_number',
            'website', 'location', 'birth_date'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if hasattr(self, 'instance') and self.instance:
            # Check if email changed and if new email already exists
            if (self.instance.email != email and
                    User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists()):
                raise ValidationError("A user with this email address already exists.")
        return email.lower()


class UserPreferencesForm(BaseForm):
    """User preferences form"""

    email_notifications = forms.BooleanField(required=False)
    notification_type = forms.ChoiceField(
        choices=UserProfile.NOTIFICATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    theme_preference = forms.ChoiceField(
        choices=UserProfile.THEME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    profile_public = forms.BooleanField(required=False)
    show_email = forms.BooleanField(required=False)
    show_phone = forms.BooleanField(required=False)


class AvatarUploadForm(forms.Form):
    """Avatar upload form"""

    avatar = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("Avatar file size cannot exceed 5MB.")

            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if avatar.content_type not in allowed_types:
                raise ValidationError("Please upload a valid image file (JPEG, PNG, or GIF).")

        return avatar


class PasswordResetRequestForm(BaseForm):
    """Password reset request form"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'x-model': 'email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError("No account found with this email address.")
        return email.lower()


class PasswordResetForm(BaseForm):
    """Password reset form"""

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'x-model': 'password1'
        }),
        min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'x-model': 'password2'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")

        return cleaned_data

