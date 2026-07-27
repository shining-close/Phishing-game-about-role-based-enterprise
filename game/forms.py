from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserModel

# User registration form: add job role selection field
from django import forms
from .models import UserModel

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

    