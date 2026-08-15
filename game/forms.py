from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserModel, RoleChangeApply

# User registration form: add job role selection field
class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Please enter your password"}
        )
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Please enter your password again"}
        )
    )
    class Meta:
        model = UserModel
        # 加上 email
        fields = ["username", "email", "role"]
        widgets = {
            "username": forms.TextInput(
                attrs={"placeholder": "Please enter your username"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "Please enter your email address"}
            ),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (k, v) for k, v in UserModel.ROLE_CHOICES if k != "admin"
        ]
    def clean_password_confirm(self):
        pwd1 = self.cleaned_data.get("password")
        pwd2 = self.cleaned_data.get("password_confirm")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError("Two entered passwords are inconsistent")
        return pwd2
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# Custom login form with placeholder prompts
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Enter your username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Enter your password"})
    )

# New: Password‑modification form
class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label="Original Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Input current password"})
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "At least 6 characters"})
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat new password"})
    )

    def clean_new_password(self):
        pwd = self.cleaned_data.get("new_password")
        if len(pwd) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long")
        return pwd

    def clean(self):
        cleaned = super().clean()
        np = cleaned.get("new_password")
        cp = cleaned.get("confirm_password")
        if np and cp and np != cp:
            self.add_error("confirm_password", "Two new passwords do not match")
        return cleaned

# New Addition: Identity Switch Application Form
class RoleApplyForm(forms.ModelForm):
    class Meta:
        model = RoleChangeApply
        fields = ["target_role"]
        widgets = {
            "target_role": forms.Select()
        }
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Filter out the user's current role; the same identity cannot be applied for.
        if current_user:
            self.fields["target_role"].choices = [
                (val, name) for val, name in UserModel.ROLE_CHOICES
                if val != current_user.role
            ]