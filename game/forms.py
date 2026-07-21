from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserModel

# User registration form: add job role selection field
from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import UserModel

class RegisterForm(forms.ModelForm):
    # 新增二次确认密码字段
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],  # 启用Django默认密码强度校验
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )

    class Meta:
        model = UserModel
        fields = ["username", "email", "password", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 过滤掉admin角色，注册仅展示hr/finance/it
        self.fields["role"].choices = [
            (k, v) for k, v in UserModel.ROLE_CHOICES if k != "admin"
        ]

    # 校验两次密码一致
    def clean_password2(self):
        pwd1 = self.cleaned_data.get("password")
        pwd2 = self.cleaned_data.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError("Two passwords are inconsistent")
        return pwd2

    # 拦截非法admin注册
    def clean_role(self):
        selected_role = self.cleaned_data.get("role")
        if selected_role == "admin":
            raise forms.ValidationError("You cannot register as administrator")
        return selected_role

    # 保存时使用Django加密密码
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

    