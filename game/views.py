from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from .forms import RegisterForm, LoginForm
from .models import EmailTemplateModel, GameRecordModel
from django.core.paginator import Paginator
from django.db.models import Max

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

# ====================== New:HR ======================
@login_required
@role_permit("hr")
def hr_l1_1(request):
    email = get_object_or_404(
        EmailTemplateModel,
        department="hr",
        difficulty_level=1
    )

    return render(request, "train/hr/l1_1.html", {"email": email})

@login_required
@role_permit("hr")
def hr_l1_2(request):
    email = get_object_or_404(EmailTemplateModel, id=2, department="hr")
    return render(request, "train/hr/l1_2.html", {"email": email})

@login_required
@role_permit("hr")
def hr_l2_1(request):
    email = get_object_or_404(EmailTemplateModel, id=3, department="hr")
    return render(request, "train/hr/l2_1.html", {"email": email})

@login_required
@role_permit("hr")
def hr_l2_2(request):
    email = get_object_or_404(EmailTemplateModel, id=4, department="hr")
    return render(request, "train/hr/l2_2.html", {"email": email})

@login_required
@role_permit("hr")
def hr_l3_1(request):
    email = get_object_or_404(EmailTemplateModel, id=5, department="hr")
    return render(request, "train/hr/l3_1.html", {"email": email})

@login_required
@role_permit("hr")
def hr_l3_2(request):
    email = get_object_or_404(EmailTemplateModel, id=6, department="hr")
    return render(request, "train/hr/l3_2.html", {"email": email})

# ===================== Finance 游戏视图 role="finance" =====================
@login_required
@role_permit("finance")
def fin_l1_1(request):
    email = get_object_or_404(EmailTemplateModel, id=7, department="finance")
    return render(request, "train/finance/l1_1.html", {"email": email})

@login_required
@role_permit("finance")
def fin_l1_2(request):
    email = get_object_or_404(EmailTemplateModel, id=8, department="finance")
    return render(request, "train/finance/l1_2.html", {"email": email})

@login_required
@role_permit("finance")
def fin_l2_1(request):
    email = get_object_or_404(EmailTemplateModel, id=9, department="finance")
    return render(request, "train/finance/l2_1.html", {"email": email})

@login_required
@role_permit("finance")
def fin_l2_2(request):
    email = get_object_or_404(EmailTemplateModel, id=10, department="finance")
    return render(request, "train/finance/l2_2.html", {"email": email})

@login_required
@role_permit("finance")
def fin_l3_1(request):
    email = get_object_or_404(EmailTemplateModel, id=11, department="finance")
    return render(request, "train/finance/l3_1.html", {"email": email})

@login_required
@role_permit("finance")
def fin_l3_2(request):
    email = get_object_or_404(EmailTemplateModel, id=12, department="finance")
    return render(request, "train/finance/l3_2.html", {"email": email})

# ===================== IT 游戏视图 role="it" =====================
@login_required
@role_permit("it")
def it_l1_1(request):
    email = get_object_or_404(EmailTemplateModel, id=13, department="it")
    return render(request, "train/it/l1_1.html", {"email": email})

@login_required
@role_permit("it")
def it_l1_2(request):
    email = get_object_or_404(EmailTemplateModel, id=14, department="it")
    return render(request, "train/it/l1_2.html", {"email": email})

@login_required
@role_permit("it")
def it_l2_1(request):
    email = get_object_or_404(EmailTemplateModel, id=15, department="it")
    return render(request, "train/it/l2_1.html", {"email": email})

@login_required
@role_permit("it")
def it_l2_2(request):
    email = get_object_or_404(EmailTemplateModel, id=16, department="it")
    return render(request, "train/it/l2_2.html", {"email": email})

@login_required
@role_permit("it")
def it_l3_1(request):
    email = get_object_or_404(EmailTemplateModel, id=17, department="it")
    return render(request, "train/it/l3_1.html", {"email": email})

@login_required
@role_permit("it")
def it_l3_2(request):
    email = get_object_or_404(EmailTemplateModel, id=18, department="it")
    return render(request, "train/it/l3_2.html", {"email": email})

# ===================== 游戏提交接口（自动生成 TP/TN/FP/FN 指标，论文RQ2/RQ3） =====================
@login_required
def submit_game_record(request):
    # 只允许POST表单提交，GET直接跳收件箱
    if request.method != "POST":
        return redirect("inbox")

    # 1. 获取表单提交全部参数
    user = request.user                                  # 当前登录训练用户
    email_id = request.POST.get("email_id")              # 当前作答邮件ID
    user_judge = request.POST.get("user_judge")           # 用户判断：phish / legit
    conf = int(request.POST.get("confidence", 3))        # 用户自信度1-5，无传参默认3
    scam_tag = request.POST.get("scam_type", "")         # 诈骗类型标签（页面写死fake_recruit_cv）

    # 2. 根据ID获取当前作答邮件数据库对象
    email_obj = get_object_or_404(EmailTemplateModel, id=email_id)
    real_label = email_obj.email_label                   # 邮件真实分类 phish/legit

    # 修复自信度转换报错
    conf_raw = request.POST.get("confidence", "")
    if conf_raw.strip() and conf_raw.isdigit():
        conf = int(conf_raw)
    else:
        conf = 3
    scam_tag = request.POST.get("scam_type", "")

    # 3. 四分类混淆矩阵计算核心逻辑
    if real_label == "phish" and user_judge == "phish":
        res = "TP"  # 真阳性：正确识别钓鱼邮件
    elif real_label == "legit" and user_judge == "legit":
        res = "TN"  # 真阴性：正确识别正规邮件
    elif real_label == "legit" and user_judge == "phish":
        res = "FP"  # 假阳性：正常邮件误判钓鱼（误报）
    else:
        res = "FN"  # 假阴性：钓鱼邮件误判正常（漏报，高危）

    # 4. 写入游戏作答记录到数据库 GameRecordModel
    GameRecordModel.objects.create(
        user=user,
        target_email=email_obj,
        judge_result=res,          # 存入TP/TN/FP/FN分类结果
        confidence_score=conf,     # 存入用户自主选择的自信分数1-5
        scam_type_tag=scam_tag
    )

    # 页面提示+跳转训练收件箱
    messages.success(request, "Judgement saved, return to training inbox.")
    return redirect("inbox")

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

# ====================== 3. 普通用户查看自己错题记录（FN漏判、FP误判） ======================
@login_required
@login_required
@login_required
def user_error_record(request):
    # 第一步：按邮件分组，只保留每道题最新一条错题记录（全局去重）
    unique_email_ids = GameRecordModel.objects.filter(
        user=request.user,
        judge_result__in=["FN", "FP"]
    ).values("target_email_id").annotate(
        latest_record_id=Max("id")
    ).values_list("latest_record_id", flat=True)

    # 第二步：根据唯一ID取出完整数据
    unique_error_records = GameRecordModel.objects.filter(
        id__in=unique_email_ids
    ).select_related("target_email").order_by("-id")

    # 第三步：分页，每页10条（已经是去重后的数据，模板无需再过滤）
    paginator = Paginator(unique_error_records, 10)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    return render(
        request,
        "profile/error_record.html",
        {"page": page_obj}
    )

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