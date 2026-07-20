from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserModel

# User registration form: add job role selection field
class RegisterForm(UserCreationForm):
    class Meta:
        model = UserModel
        # Required input fields for new account
        fields = ["username", "email", "role", "password1", "password2"]
        # Add CSS style for role dropdown selector
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
        }

# Custom login form with placeholder prompts
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Enter your username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Enter your password"})
    )

    