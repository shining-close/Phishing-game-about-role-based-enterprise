from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from .forms import RegisterForm, LoginForm
from .models import EmailTemplateModel, GameRecordModel, Level2EmailTemplateModel
from django.core.paginator import Paginator
from django.db.models import Max
import random
from django.core.paginator import Paginator



# Difine a decorator to restrict access to views based on user role
def role_permit(allow_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != allow_role:
                messages.error(request, "This training page only belongs to your department.")
                return redirect("inbox")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

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

# ====================== Train ======================
import random
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import EmailTemplateModel, Level2EmailTemplateModel, GameRecordModel

# ====================== Train Level 1 ======================
@login_required
def train_level1_view(request):
    user_dept = request.user.role
    train_question_list = []
    for serial_num in [1,2,3,4,5]:
        serial_all_mail = EmailTemplateModel.objects.filter(
            department=user_dept,
            difficulty_level=1,
            template_serial=serial_num
        )
        mail_list = list(serial_all_mail)
        if len(mail_list) == 0:
            msg = f"L1 template serial {serial_num} has no emails. Please contact admin to add templates."
            return render(request, "train/error_tip.html", {"msg": msg})
        pick_one = random.choice(mail_list)
        train_question_list.append(pick_one)
    random.shuffle(train_question_list)
    request.session["train_queue"] = [obj.id for obj in train_question_list]
    request.session["train_idx"] = 0
    return redirect("train_question", tpl_id=train_question_list[0].id, level=1)

@login_required
def train_question(request, level, tpl_id):
    train_queue = request.session.get("train_queue", [])
    current_idx = request.session.get("train_idx", 0)
    # 校验session队列合法性
    if not train_queue or current_idx >= len(train_queue) or train_queue[current_idx] != tpl_id:
        return redirect(f"train_l{level}")

    template = None
    template_file = ""
    try:
        if level == 1:
            template = EmailTemplateModel.objects.get(id=tpl_id)
            template_file = f"train/L1/L1_{template.template_serial}.html"
        elif level == 2:
            template = Level2EmailTemplateModel.objects.get(id=tpl_id)
            template_file = f"train/L2/{template.template_type}.html"
        elif level == 3:
            template = EmailTemplateModel.objects.get(id=tpl_id)
            template_file = f"train/L1/L1_{template.template_serial}.html"
    except (EmailTemplateModel.DoesNotExist, Level2EmailTemplateModel.DoesNotExist):
        # 模板已删除，清空训练会话，重置训练
        if "train_queue" in request.session:
            del request.session["train_queue"]
        if "train_idx" in request.session:
            del request.session["train_idx"]
        messages.warning(request, "Some training emails were removed, training restarted.")
        return redirect(f"train_l{level}")

    if request.method == "POST":
        return submit_game_record(request)

    total_count = len(train_queue)
    current_num = current_idx + 1
    return render(request, template_file, {
        "template": template,
        "level": level,
        "current_num": current_num,
        "total_count": total_count
    })

def train_complete(request):
    if "train_queue" in request.session:
        del request.session["train_queue"]
    if "train_idx" in request.session:
        del request.session["train_idx"]
    return render(request, "train/train_complete.html")

def train_error_tip(request):
    msg = request.GET.get("msg", "Question bank abnormal, contact administrator")
    return render(request, "train/error_tip.html", {"msg": msg})

# ====================== Train Level 2 ======================
@login_required
def train_level2_view(request):
    user_dept = request.user.role
    template_list = list(Level2EmailTemplateModel.objects.filter(
        department=user_dept,
        difficulty_level=2
    ))
    if len(template_list) < 5:
        return render(request, "train/error_tip.html", {"msg": "L2 question bank has less than 5 emails"})
    random.shuffle(template_list)
    request.session["train_queue"] = [t.id for t in template_list]
    request.session["train_idx"] = 0
    return redirect("train_question", level=2, tpl_id=template_list[0].id)

# ====================== Train Level 3 ======================
@login_required
def train_level3_view(request):
    user_dept = request.user.role
    template_list = list(EmailTemplateModel.objects.filter(
        department=user_dept,
        difficulty_level=3,
        email_label="phish"
    ))
    if len(template_list) < 5:
        msg = "L3 question bank lacks 5 phishing templates, contact admin to add."
        return render(request, "train/error_tip.html", {"msg": msg})
    random.shuffle(template_list)
    request.session["train_queue"] = [t.id for t in template_list]
    request.session["train_idx"] = 0
    return redirect("train_question", tpl_id=template_list[0].id, level=3)

# ====================== Submit Game Record ======================
@login_required
def submit_game_record(request):
    if request.method != "POST":
        return redirect("inbox")

    user = request.user
    email_id = request.POST.get("email_id")
    level = request.POST.get("level", "1")
    user_judge = request.POST.get("judge_result")

    conf_raw = request.POST.get("confidence", "")
    conf = 3
    if conf_raw.strip() and conf_raw.isdigit():
        conf = int(conf_raw)

    scam_tag = request.POST.get("scam_type", "")
    email_obj = None
    try:
        if level == "1" or level == "3":
            email_obj = EmailTemplateModel.objects.get(id=email_id)
        elif level == "2":
            email_obj = Level2EmailTemplateModel.objects.get(id=email_id)
    except (EmailTemplateModel.DoesNotExist, Level2EmailTemplateModel.DoesNotExist):
        if "train_queue" in request.session:
            del request.session["train_queue"]
        if "train_idx" in request.session:
            del request.session["train_idx"]
        messages.warning(request, "Training email missing, restart training.")
        return redirect(f"train_l{level}")

    real_label = email_obj.email_label
    res = "right" if user_judge == real_label else "wrong"

    if level == "1" or level == "3":
        GameRecordModel.objects.create(
            user=user,
            target_email=email_obj,
            target_l2_email=None,
            judge_result=res,
            confidence_score=conf,
            scam_type_tag=scam_tag
        )
    elif level == "2":
        GameRecordModel.objects.create(
            user=user,
            target_email=None,
            target_l2_email=email_obj,
            judge_result=res,
            confidence_score=conf,
            scam_type_tag=scam_tag
        )

    # ==========【核心修复：更新当前题号索引存入session】==========
    current_idx = request.session.get("train_idx", 0)
    next_idx = current_idx + 1
    request.session["train_idx"] = next_idx  # 必须这一行！

    queue = request.session["train_queue"]
    if next_idx >= len(queue):
        # 全部题目做完 → 跳转训练完成页面
        return redirect("train_complete")
    # 进入下一题
    return redirect("train_question", level=level, tpl_id=queue[next_idx])

# ====================== User Wrong Record ======================
@login_required
def user_error_record(request):
    from django.core.paginator import Paginator
    all_wrong = GameRecordModel.objects.filter(
        user=request.user,
        judge_result="wrong"
    ).select_related("target_email", "target_l2_email").order_by("-operation_timestamp")

    seen_keys = set()
    unique_list = []
    for rec in all_wrong:
        key = None
        if rec.target_email:
            key = f"L1_{rec.target_email.id}"
        elif rec.target_l2_email:
            key = f"L2_{rec.target_l2_email.id}"
        if key and key not in seen_keys:
            seen_keys.add(key)
            unique_list.append(rec)

    paginator = Paginator(unique_list, 10)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)
    return render(request, "profile/error_record.html", {"page": page_obj})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .models import UserModel, GameRecordModel, RoleChangeApply, EmailTemplateModel

# 判断是否管理员
def is_admin(user):
    return user.is_authenticated and user.role == "admin"

# ====================== 1. 个人中心首页 ======================
@login_required
def profile_center(request):
    return render(request, "profile/profile.html", {"user": request.user})

# ====================== 2. 修改密码（所有登录用户可用） ======================
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect("profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "profile/change_pwd.html", {"form": form})

# ====================== 4. 用户提交角色变更申请 ======================
@login_required
def apply_change_role(request):
    if request.method == "POST":
        target_role = request.POST.get("target_role")
        # 不能申请当前角色、不能申请admin（只有后台创建管理员）
        if target_role == request.user.role or target_role == "admin":
            messages.error(request, "Invalid target role! Cannot apply admin or your current role.")
            return redirect("apply_role")
        # 检查是否存在待审核申请
        exist_apply = RoleChangeApply.objects.filter(user=request.user, status="pending").exists()
        if exist_apply:
            messages.error(request, "You already have a pending role change application!")
            return redirect("profile")
        # 创建申请单
        RoleChangeApply.objects.create(
            user=request.user,
            target_role=target_role
        )
        messages.success(request, "Application submitted, waiting for admin review.")
        return redirect("profile")
    # GET 渲染选择角色下拉
    role_choices = [r for r in UserModel.ROLE_CHOICES if r[0] != "admin"]
    return render(request, "profile/apply_role.html", {"role_choices": role_choices})

# ====================== 5. 管理员：角色变更申请列表 ======================
@login_required
def admin_role_audit_list(request):
    if not is_admin(request.user):
        messages.error(request, "Permission denied, only admin can access this page.")
        return redirect("profile")
    all_apply = RoleChangeApply.objects.all().select_related("user").order_by("-apply_time")
    return render(request, "manage/role_audit_list.html", {"apply_list": all_apply})

# ====================== 6. 管理员处理申请（通过/驳回） ======================
@login_required
def deal_role_apply(request, apply_id):
    if not is_admin(request.user):
        messages.error(request, "Permission denied.")
        return redirect("profile")
    apply_obj = get_object_or_404(RoleChangeApply, id=apply_id)
    if apply_obj.status != "pending":
        messages.warning(request, "This application has already been processed.")
        return redirect("admin_role_audit")
    if request.method == "POST":
        operate = request.POST.get("operate")
        remark = request.POST.get("remark", "")
        if operate == "approve":
            # 通过：直接修改用户角色
            apply_obj.user.role = apply_obj.target_role
            apply_obj.user.save()
            apply_obj.status = "approved"
        elif operate == "reject":
            apply_obj.status = "rejected"
        apply_obj.admin_remark = remark
        apply_obj.audit_admin = request.user
        apply_obj.save()
        messages.success(request, "Audit operation completed.")
        return redirect("admin_role_audit")
    return render(request, "manage/deal_apply.html", {"item": apply_obj})

# ====================== 7. 管理员查看所有用户完整数据 ======================
# 页面1：所有用户分页列表，每页20条
@login_required
def admin_all_user_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrator can access this page.")
        return redirect("profile")
    user_queryset = UserModel.objects.all().order_by("id")
    paginator = Paginator(user_queryset, 20)  # 每页20条
    page_num = request.GET.get("page", 1)
    page_data = paginator.get_page(page_num)
    return render(request, "manage/all_user_list.html", {"page": page_data})

# 页面2：所有训练日志分页列表，每页20条
@login_required
def admin_all_game_logs(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrator can access this page.")
        return redirect("profile")
    log_queryset = GameRecordModel.objects.all().select_related("user", "target_email").order_by("-operation_timestamp")
    paginator = Paginator(log_queryset, 20)
    page_num = request.GET.get("page", 1)
    page_data = paginator.get_page(page_num)
    return render(request, "manage/all_game_logs.html", {"page": page_data})