from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from .models import EmailTemplateModel

# User registration page: redirect authenticated users to inbox
def register_view(request):
    if request.user.is_authenticated:
        return redirect("inbox")
    register_form = RegisterForm()
    # Handle POST submission when user submits register form
    if request.method == "POST":
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            # Save new user record to database
            new_user = register_form.save()
            # Auto login after successful registration
            login(request, new_user)
            return redirect("inbox")
    return render(request, "register.html", {"form": register_form})

# User login page
def login_view(request):
    if request.user.is_authenticated:
        return redirect("inbox")
    login_form = LoginForm()
    if request.method == "POST":
        login_form = LoginForm(request, data=request.POST)
        if login_form.is_valid():
            login_user = login_form.get_user()
            login(request, login_user)
            return redirect("inbox")
    return render(request, "login.html", {"form": login_form})

# Logout function: clear session and redirect to login page
def logout_view(request):
    logout(request)
    return redirect("login")

# Core inbox page: ONLY load emails matching current user's department role
# Decorator @login_required blocks unauthenticated access
@login_required
def inbox_view(request):
    # Fetch logged-in user's assigned department role
    current_user_role = request.user.role
    # Filter email dataset: only display emails belonging to user's role
    role_specific_emails = EmailTemplateModel.objects.filter(department=current_user_role).order_by("-created_at")
    return render(request, "inbox.html", {
        "active_user": request.user,
        "email_dataset": role_specific_emails
    })

def home_view(request):
    """Home page with English welcome text for phishing simulation test"""
    return render(request, "home.html")