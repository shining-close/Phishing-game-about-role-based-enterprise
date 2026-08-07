from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from .forms import RegisterForm, LoginForm, ChangePasswordForm, RoleApplyForm
# 更新导入模型：移除GameRecordModel，导入新表
from .models import (
    EmailTemplateModel, Level2EmailTemplateModel,
    PreTestRecord, TrainSession, UserMailAction,
    UserModel, RoleChangeApply, UserEmailAudit
)
from django.core.paginator import Paginator
import random
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Max, OuterRef, Subquery, Q
import json
import re

# Difine a decorator to restrict access to views based on user role
def role_permit(allow_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != allow_role:
                messages.error(request, "This page only belongs to your department.")
                return redirect("home")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# ====================== 登录注册登出（完全无需修改） ======================
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    register_form = RegisterForm()
    if request.method == "POST":
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            new_user = register_form.save()
            login(request, new_user)
            return redirect("home")
    return render(request, "register.html", {"form": register_form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    login_form = LoginForm()
    if request.method == "POST":
        login_form = LoginForm(request, data=request.POST)
        if login_form.is_valid():
            login_user = login_form.get_user()
            login(request, login_user)
            return redirect("home")
    return render(request, "login.html", {"form": login_form})

def logout_view(request):
    logout(request)
    return redirect("login")

# ====================== 首页（控制按钮解锁状态） ======================
@login_required
def home_view(request):
    user = request.user
    # 仅保留数据查询（报表/个人中心仍会用到，首页不再做锁定）
    has_pretest = PreTestRecord.objects.filter(user=user).exists()
    can_l3 = user.unlock_l3
    l2_total = user.l2_total_points
    return render(request, "home.html", {
        "has_pretest": has_pretest,
        "can_l3": can_l3,
        "l2_total": l2_total,
        "user": user
    })

# ====================== 1. 前置预测试 PreTest（原Level1逻辑改造） ======================
@login_required
def pretest_start(request):
    user_dept = request.user.role
    train_question_list = []
    for serial_num in [1,2,3,4,5]:
        serial_all_mail = EmailTemplateModel.objects.filter(
            department=user_dept,
            template_serial=serial_num
        )
        mail_list = list(serial_all_mail)
        if len(mail_list) == 0:
            msg = f"PreTest template serial {serial_num} missing, contact admin."
            return render(request, "train/error_tip.html", {"msg": msg})
        pick_one = random.choice(mail_list)
        train_question_list.append(pick_one)
    random.shuffle(train_question_list)
    request.session["pretest_queue"] = [obj.id for obj in train_question_list]
    request.session["pretest_idx"] = 0
    return redirect("pretest_question", tpl_id=train_question_list[0].id)

@login_required
def pretest_question(request, tpl_id):
    train_queue = request.session.get("pretest_queue", [])
    current_idx = request.session.get("pretest_idx", 0)
    if not train_queue or current_idx >= len(train_queue) or train_queue[current_idx] != tpl_id:
        return redirect("pretest_start")
    template = get_object_or_404(EmailTemplateModel, id=tpl_id)

    # 根据serial拼接子模板路径 L1_1.html ~ L1_5.html
    sub_template_path = f"train/L1/L1_{template.template_serial}.html"
    template_file = "train/L1/base_normalemail.html"

    if request.method == "POST":
        return submit_pretest_record(request)
    total_count = len(train_queue)
    current_num = current_idx + 1
    return render(request, template_file, {
        "template": template,
        "current_num": current_num,
        "total_count": total_count,
        "sub_template": sub_template_path
    })

# 提交预测试答案，存入PreTestRecord，全部完成计算基线分数
@login_required
def submit_pretest_record(request):
    if request.method != "POST":
        return redirect("home")
    user = request.user
    email_id = request.POST.get("email_id")
    user_judge = request.POST.get("judge_result")
    conf_raw = request.POST.get("confidence", "3")
    conf = int(conf_raw) if conf_raw.isdigit() else 3
    scam_tag = request.POST.get("scam_type", "")
    email_obj = get_object_or_404(EmailTemplateModel, id=email_id)
    real_label = email_obj.email_label
    res = "right" if user_judge == real_label else "wrong"
    # 新建预测试记录（替代GameRecordModel）
    PreTestRecord.objects.create(
        user=user,
        target_email=email_obj,
        judge_result=res,
        confidence_score=conf,
        scam_type_tag=scam_tag
    )
    current_idx = request.session.get("pretest_idx", 0)
    next_idx = current_idx + 1
    request.session["pretest_idx"] = next_idx
    queue = request.session["pretest_queue"]
    if next_idx >= len(queue):
        # 全部做完，计算平均分存入pre_test_score
        all_records = PreTestRecord.objects.filter(user=user)
        total_conf = sum(r.confidence_score for r in all_records)
        avg_conf = total_conf / all_records.count()
        user.pre_test_score = round(avg_conf, 2)
        user.save()
        # 清空session
        del request.session["pretest_queue"]
        del request.session["pretest_idx"]
        return redirect("pretest_complete")
    return redirect("pretest_question", tpl_id=queue[next_idx])

# 预测试完成页
@login_required
def pretest_complete(request):
    return render(request, "train/L1/pretest_complete.html")

# ====================== 2. L2 / L3 仿真收件箱训练（全新逻辑） ======================
# 进入L2中级训练入口，权限校验：必须完成预测试
@login_required
def train_l2_inbox(request):
    user = request.user
    # 拦截未完成预测试用户
    if not PreTestRecord.objects.filter(user=user).exists():
        messages.error(request, "Complete Pre-Test first before training!")
        return redirect("pretest_start")

    # 创建本次训练会话 difficulty=2
    session = TrainSession.objects.create(user=user, difficulty=2)

    # 拉取当前用户部门 L2邮件：随机排序，一轮训练最多10封
    mail_queryset = Level2EmailTemplateModel.objects.filter(
        department=user.role,
        difficulty_level=2,
        is_available=True  # 只加载审核通过可用邮件
    ).order_by("?")[:10]
 
    if not mail_queryset.exists():
        msg = "L2 training emails are empty, contact admin."
        return render(request, "train/error_tip.html", {"msg": msg})

    mail_list = list(mail_queryset)
    return render(request, "inbox.html", {
        "session": session,
        "mail_list": mail_list,
        "diff": 2
    })

@login_required
def l2_mail_detail(request, mail_id):
    mail = get_object_or_404(Level2EmailTemplateModel, id=mail_id)
    # template_type 数据库存 L2_1 / L2_2，拼接完整路径
    sub_template = f"train/L2/{mail.template_type}.html"
    return render(request, "train/L2/_mail_preview.html", {
        "template": mail,
        "sub_template": sub_template
    })

# 进入L3高级训练入口，双重校验：预测试完成 + L2累计≥30分解锁
@login_required
def train_l3_inbox(request):
    user = request.user
    if not PreTestRecord.objects.filter(user=user).exists():
        messages.error(request, "Complete Pre-Test first before training!")
        return redirect("pretest_start")
    if not user.unlock_l3:
        messages.error(request, f"Need total 30 L2 points to unlock L3, current:{user.l2_total_points}")
        return redirect("home")
    session = TrainSession.objects.create(user=user, difficulty=3)
    mail_list = list(Level2EmailTemplateModel.objects.filter(
        department=user.role, difficulty_level=3
    ).order_by("?"))
    if not mail_list:
        msg = "L3 training emails are empty, contact admin."
        return render(request, "train/error_tip.html", {"msg": msg})
    return render(request, "inbox.html", {
        "session": session,
        "mail_list": mail_list,
        "diff": 3
    })

# Lv3 用户创建钓鱼邮件编辑器入口
@login_required
def level3_editor(request):
    user = request.user
    # 双重校验：完成预测试 + L2积分达标解锁L3
    if not PreTestRecord.objects.filter(user=user).exists():
        messages.error(request, "Complete Pre-Test first before creating emails.")
        return redirect("pretest_start")
    if not user.unlock_l3:
        messages.error(request, f"You need at least 30 L2 points to unlock Level3 creation, current: {user.l2_total_points}")
        return redirect("home")
    # 传给模板用户自身岗位，前端固定不可修改
    return render(request, "train/l3/editor.html", {
        "user_dept": user.role
    })

# L3提交自制邮件，进入管理员审核
@login_required
def submit_user_created_mail(request):
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect("level3_editor")
    user = request.user
    sender = request.POST.get("sender", "")
    subject = request.POST.get("subject", "")
    c1 = request.POST.get("content_1", "")
    link_text_1 = request.POST.get("link_text_1", "")
    u1 = request.POST.get("url_1", "")
    c2 = request.POST.get("content_2", "")
    link_text_2 = request.POST.get("link_text_2", "")
    u2 = request.POST.get("url_2", "")
    c3 = request.POST.get("content_3", "")
    link_text_3 = request.POST.get("link_text_3", "")
    u3 = request.POST.get("url_3", "")
    c4 = request.POST.get("content_4", "")
    link_text_4 = request.POST.get("link_text_4", "")
    u4 = request.POST.get("url_4", "")
    email_label = request.POST.get("phish", "")
    scam_keywords = request.POST.get("scam_keywords", "")
    analysis_desc = request.POST.get("analysis_description", "")

    # 不再读取前端难度，直接固定为2
    diff = 2
    template_type = request.POST.get("template_type", "")
    dept = user.role
    source_type = "user_submit"

    # 基础校验
    if not sender or not subject:
        messages.error(request, "Sender and Subject cannot be empty.")
        return redirect("level3_editor")
    # 移除难度数字校验，diff固定2无需判断
    # 校验模板不能为空
    if not template_type:
        messages.error(request, "You must select a template file.")
        return redirect("level3_editor")

    # 创建邮件模板
    new_mail = Level2EmailTemplateModel.objects.create(
        sender=sender,
        subject=subject,
        content_1=c1,
        link_text_1=link_text_1,
        url_1=u1,
        content_2=c2,
        link_text_2=link_text_2,
        url_2=u2,
        content_3=c3,
        link_text_3=link_text_3,
        url_3=u3,
        content_4=c4,
        link_text_4=link_text_4,
        url_4=u4,
        difficulty_level=diff, # 固定2
        template_type=template_type,
        email_label=email_label,
        department=dept,
        scam_keywords=scam_keywords,
        analysis_description=analysis_desc,
        source=source_type
    )
    # 创建审核记录对象
    audit_record = UserEmailAudit.objects.create(
        creator=user,
        email_template=new_mail
    )
    # 自动打分逻辑不变
    s1, s2, s3, s4, total, grade, suggest = calc_phish_score(new_mail)
    audit_record.score_dept_match = s1
    audit_record.score_social_engineer = s2
    audit_record.score_fake_tech = s3
    audit_record.score_flaw = s4
    audit_record.total_score = total
    audit_record.level_grade = grade
    audit_record.score_suggest = suggest
    audit_record.save()

    messages.success(request, "Your email draft has been submitted, waiting for administrator review.")
    return redirect("my_submit_mail_list")

# AJAX 保存用户操作行为（打开/标记/删除/点击链接）
@login_required
def mail_action_save(request):
    if request.method != "POST":
        return JsonResponse({"code": 400, "msg": "Invalid request"})
    session_id = request.POST.get("session_id")
    mail_id = request.POST.get("mail_id")
    action_type = request.POST.get("action")

    # 参数空值校验
    if not session_id or not mail_id or not action_type:
        return JsonResponse({"code":400, "msg":"缺少参数"})

    try:
        session_obj = get_object_or_404(TrainSession, id=session_id, user=request.user)
        mail_obj = get_object_or_404(Level2EmailTemplateModel, id=mail_id)
        # 匹配你原有模型字段 session / mail
        UserMailAction.objects.create(
            session=session_obj,
            mail=mail_obj,
            action_type=action_type
        )
        return JsonResponse({"code": 200, "msg": "success"})
    except Exception as e:
        print("操作保存异常：", str(e))
        return JsonResponse({"code": 500, "msg": str(e)})

# 结束本次训练，计算总分、统计正确识别数量、自动解锁L3
@login_required
def finish_train_session(request):
    if request.method != "POST":
        return redirect("train_l2")
    session_id = request.POST.get("session_id")
    train_session = get_object_or_404(TrainSession, id=session_id, user=request.user)
    user = train_session.user
    all_actions = UserMailAction.objects.filter(session=train_session).select_related("mail")
    mail_final_judge = {}
    clicked_phish_mail_ids = set()
    for act in all_actions.order_by("action_time"):
        if act.action_type == "click_link":
            if act.mail.email_label == "phish":
                clicked_phish_mail_ids.add(act.mail.id)
        else:
            mail_final_judge[act.mail.id] = act
    score = 0
    max_total = 30
    correct_count = 0
    wrong_count = 0
    # 处理判定计分
    for mail_id, action in mail_final_judge.items():
        mail_template = action.mail
        act_type = action.action_type
        if act_type == "report_phish":
            if mail_template.email_label == "phish":
                score += 6
                correct_count += 1
            else:
                score -= 4
                wrong_count += 1
        elif act_type == "mark_legit":
            if mail_template.email_label == "legit":
                score += 6
                correct_count += 1
            else:
                score -= 4
                wrong_count += 1
    # 钓鱼链接扣分，一封只扣一次
    score -= len(clicked_phish_mail_ids) * 6
    final_score = max(0, min(score, max_total))
    # ===========核心改动：根据分数判断是否通关、永久解锁L3、累计用户L2积分===========
    pass_level2 = final_score >= 30
    train_session.total_score = final_score
    train_session.end_time = timezone.now()
    train_session.correct_identify = correct_count
    train_session.wrong_identify = wrong_count
    train_session.pass_level2 = pass_level2
    train_session.save()

    # 1. 用户累加本次得分到l2_total_points
    user.l2_total_points += final_score
    # 2. 只要本次分数≥30，永久解锁L3，不会再关闭
    if pass_level2 and not user.unlock_l3:
        user.unlock_l3 = True
    # 保存用户全局数据
    user.save()
    # 调用模型方法校验解锁（兼容原有逻辑）
    user.check_unlock_l3()

    return redirect("train_report", session_id=session_id)
# 训练报告页面
@login_required
def train_report(request, session_id):
    session_obj = get_object_or_404(TrainSession, id=session_id, user=request.user)
    all_actions = UserMailAction.objects.filter(session=session_obj).select_related("mail").order_by("action_time")
    # 1. 标记哪些钓鱼邮件已经扣过分（用于控制delta分值）
    deducted_phish_mail = set()
    detail_list = []
    total_add = 0
    total_minus = 0
    action_name_map = {
        "mark_suspicious": "Mark Suspicious",
        "mark_legit": "Mark Legitimate",
        "delete_mail": "Delete Mail",
        "report_phish": "Report Phishing",
        "click_link": "Click Hyperlink",
        "open_mail": "Open Email"
    }
    for act in all_actions:
        mail = act.mail
        act_type = act.action_type
        delta = 0
        reason = ""
        if act_type == "report_phish":
            if mail.email_label == "phish":
                delta = 6
                total_add += 6
                reason = "Real phishing email, correct identification"
            else:
                delta = -4
                total_minus += 4
                reason = "Legitimate email, false report"
        elif act_type == "mark_legit":
            if mail.email_label == "legit":
                delta = 6
                total_add += 6
                reason = "Legitimate email, correct identification"
            else:
                delta = -4
                total_minus += 4
                reason = "Phishing email, misjudged as normal"
        elif act_type == "click_link":
            if mail.email_label == "phish":
                # 判断是否已经扣过分
                if mail.id not in deducted_phish_mail:
                    delta = -6
                    total_minus += 6
                    deducted_phish_mail.add(mail.id)
                    reason = "First click of links in this phishing mail, deduct 6 points"
                else:
                    delta = 0
                    reason = "Repeated clicks on links of the same phishing mail, no repeated deduction"
            else:
                delta = 0
                reason = "Clicked link in legitimate email, no score deduction"
        else:
            reason = "No score adjustment"
        display_action = action_name_map.get(act_type, act_type)
        detail_list.append({
            "time": act.action_time,
            "action_name": display_action,
            "mail_title": mail.subject,
            "mail_type": mail.email_label,
            "delta": delta,
            "reason": reason
        })
    # =========新增：计算最终得分=========
    raw_score = total_add - total_minus
    final_score = raw_score
    if final_score > 30:
        final_score = 30
    if final_score < 0:
        final_score = 0

    return render(request, "train/report.html", {
        "session": session_obj,
        "detail_list": detail_list,
        "total_add": total_add,
        "total_minus": total_minus,
        "final_score": final_score  # 传给模板使用
    })

def calc_phish_score(mail_obj):
    """
    输入 Level2EmailTemplateModel 对象，返回分项分数、总分、评级、优化建议
    返回：(s1, s2, s3, s4, total, grade, suggest_text)
    """
    # 1. 词库定义
    dept_keyword = {
        "hr": ["salary", "interview", "contract", "resign", "attendance", "staff"],
        "finance": ["invoice", "reimbursement", "payment", "budget", "tax", "fund"],
        "it": ["account", "password", "system", "login", "server", "upgrade"]
    }
    social_engineer_words = {
        "authority": ["administrator", "CEO", "manager", "official"],
        "urgent": ["immediately", "urgent", "within 1 hour", "deadline"],
        "fear_loss": ["account lock", "expire", "disable", "deduction"],
        "benefit": ["bonus", "subsidy", "refund", "reward"]
    }
    forbidden_words = ["violence", "gambling", "porn", "hack", "fraud bank card"]

    # 合并所有正文
    all_content = f"{mail_obj.content_1} {mail_obj.content_2} {mail_obj.content_3} {mail_obj.content_4}".lower()
    all_urls = [mail_obj.url_1, mail_obj.url_2, mail_obj.url_3, mail_obj.url_4]
    sender = mail_obj.sender.lower()
    target_dept = mail_obj.department

    suggest_list = []

    # ========== 维度1 岗位贴合 0-30 ==========
    base_dept_score = 0
    target_words = dept_keyword.get(target_dept, [])
    hit = sum(1 for w in target_words if w in all_content)
    base_dept_score = min(hit * 6, 30)
    if hit == 0:
        suggest_list.append(f"【岗位贴合】正文未出现{target_dept.upper()}业务关键词，场景匹配度低")
    s1 = base_dept_score

    # ========== 维度2 社会工程诱导 0-30 ==========
    s2 = 0
    for cat, words in social_engineer_words.items():
        if any(w in all_content for w in words):
            s2 += 7.5
    s2 = min(s2, 30)
    if s2 == 0:
        suggest_list.append("【诱导设计】缺少权威、紧急、利益、损失类诱导话术，钓鱼吸引力不足")

    # ========== 维度3 伪装技术 0-25 ==========
    s3 = 0
    # 发件人伪造判断
    fake_sender_reg = re.compile(r"admin.*@qq|hr.*@163|ceo.*@gmail")
    if fake_sender_reg.search(sender):
        s3 += 12
    # 仿冒URL判断
    fake_domain_reg = re.compile(r"pay.*-verify|login-safe.*top")
    url_hit = 0
    for u in all_urls:
        if u and fake_domain_reg.search(u):
            url_hit += 1
    s3 += min(url_hit * 6.5, 13)
    s3 = min(s3, 25)
    if not any(all_urls):
        suggest_list.append("【伪装技术】未填写钓鱼链接，缺少核心钓鱼载体")

    # ========== 维度4 破绽隐蔽度 0-15 ==========
    s4 = 15
    flaw_words = ["dear user", "click this link", "contact us immediately"]
    flaw_count = sum(1 for w in flaw_words if w in all_content)
    s4 -= flaw_count * 3
    s4 = max(s4, 0)
    if flaw_count > 0:
        suggest_list.append(f"【破绽控制】检测到{flaw_count}处通用低级钓鱼话术，容易被识别")

    # 违禁词直接清零
    if any(word in all_content for word in forbidden_words):
        s1 = s2 = s3 = s4 = 0
        suggest_list.append("【违规警告】邮件包含违规敏感词汇，直接判定不合格")

    total = round(s1 + s2 + s3 + s4, 1)

    # 评级
    if total >= 90:
        grade = "Excellent"
    elif total >=70:
        grade = "Good"
    elif total >=40:
        grade = "Normal"
    else:
        grade = "Poor"

    suggest_text = "\n".join(suggest_list) if suggest_list else "No optimization suggestions, well-designed phishing mail."
    return s1, s2, s3, s4, total, grade, suggest_text

# ====================== 个人中心、改密码、角色申请、管理员后台 ======================
def is_admin(user):
    return user.is_authenticated and user.role == "admin"

@login_required
def profile_center(request):
    user = request.user
    # 查询是否存在待审核角色申请
    has_pending_apply = RoleChangeApply.objects.filter(user=user, status="pending").exists()
    return render(request, "profile/profile.html", {
        "user": user,
        "has_pending_apply": has_pending_apply,
        "role_list": UserModel.ROLE_CHOICES
    })

# 修改密码（使用自定义表单，弃用原生PasswordChangeForm）
@login_required
def change_password(request):
    user = request.user
    form = ChangePasswordForm()
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            # 校验原密码
            from django.contrib.auth.hashers import check_password, make_password
            old_pwd = form.cleaned_data["old_password"]
            new_pwd = form.cleaned_data["new_password"]
            if not check_password(old_pwd, user.password):
                messages.error(request, "Original password is incorrect")
            else:
                user.password = make_password(new_pwd)
                user.save()
                # 刷新登录session，避免退出
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("profile")
    return render(request, "profile/change_pwd.html", {"form": form})

# 提交角色切换申请（使用RoleApplyForm自动过滤当前角色）
@login_required
def apply_change_role(request):
    user = request.user
    # 禁止重复提交待审核申请
    if RoleChangeApply.objects.filter(user=user, status="pending").exists():
        messages.error(request, "You have a pending role change application, cannot submit again.")
        return redirect("personal_center")

    form = RoleApplyForm(user=user)
    # 从ROLE_CHOICES剔除admin，普通用户永远看不到admin选项
    all_roles = list(UserModel.ROLE_CHOICES)
    # 移除admin选项
    all_roles = [(k,v) for k,v in all_roles if k != "admin"]
    # 再剔除自己当前角色
    filtered_roles = [(k,v) for k,v in all_roles if k != user.role]

    if request.method == "POST":
        form = RoleApplyForm(request.POST, user=user)
        if form.is_valid():
            apply_obj = form.save(commit=False)
            apply_obj.user = user
            apply_obj.save()
            messages.success(request, "Role change application submitted, waiting for administrator review.")
            return redirect("personal_center")
    # 传给模板过滤后的角色列表
    return render(request, "profile/apply_role.html", {"role_list": filtered_roles})

# 用户错题扣分记录列表：分页10条，同一邮件只保留最新扣分操作
@login_required
def user_error_records(request):
    from django.db.models import Max, OuterRef, Subquery, Q
    user = request.user
    # 子查询：当前用户【所有训练会话】里每一封邮件的最新操作ID
    latest_action_sub = UserMailAction.objects.filter(
        session__user=user,
        mail=OuterRef("mail")
    ).values("mail").annotate(max_act_id=Max("id")).values("max_act_id")

    # 第一步：筛选出每封邮件最新一次操作
    base_qs = UserMailAction.objects.filter(id__in=Subquery(latest_action_sub))

    # 第二步：只保留扣分类型操作
    error_actions = base_qs.filter(
        Q(action_type="report_phish", mail__email_label="legit")
        | Q(action_type="mark_legit", mail__email_label="phish")
        | Q(action_type="click_link", mail__email_label="phish")
    ).select_related("mail", "session").order_by("-action_time")

    paginator = Paginator(error_actions, 10)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "profile/error_record_list.html", {"page_data": page_data})

# 错题扣分详情页
@login_required
def error_record_detail(request, action_id):
    user = request.user
    action = get_object_or_404(UserMailAction, id=action_id, session__user=user)
    mail = action.mail
    act_type = action.action_type
    mail_type = mail.email_label

    score_cut = 0
    explain_text = ""
    if act_type == "report_phish" and mail_type == "legit":
        score_cut = -4
        explain_text = "You reported a normal business email as phishing mail, misjudgment, deduct 4 points."
    elif act_type == "mark_legit" and mail_type == "phish":
        score_cut = -4
        explain_text = "You judged a phishing email as normal mail, misjudgment, deduct 4 points."
    elif act_type == "click_link" and mail_type == "phish":
        score_cut = -6
        explain_text = "You clicked the malicious link in the phishing email, high-risk operation, deduct 6 points."
    else:
        score_cut = 0
        explain_text = "This operation has no score penalty."

    return render(request, "profile/error_record_detail.html", {
        "action": action,
        "mail": mail,
        "score_cut": score_cut,
        "explain_text": explain_text
    })

# 用户查看自己提交的所有待审核/已审核邮件
@login_required
def my_submit_mail_list(request):
    user = request.user
    audit_list = UserEmailAudit.objects.filter(creator=user).select_related("email_template")
    paginator = Paginator(audit_list, 10)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "profile/my_submit_mails.html", {"page_data": page_data})

@login_required
def user_submit_mail_detail(request, pk):
    # 只能查看自己提交的审核单，防止越权
    audit_record = get_object_or_404(UserEmailAudit, pk=pk, creator=request.user)
    mail = audit_record.email_template
    return render(request, "profile/user_submit_mail_detail.html", {
        "record": audit_record,
        "mail": mail
    })

# ====================== 管理员角色审核（逻辑微调，保留原有功能） ======================
@login_required
def admin_role_audit_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrators can access this page")
        return redirect("home")
    all_apply = RoleChangeApply.objects.select_related("user").order_by("-apply_time")
    return render(request, "manage/role_audit_list.html", {"apply_list": all_apply})

@login_required
def deal_role_apply(request, apply_id):
    if not is_admin(request.user):
        messages.error(request, "Permission denied")
        return redirect("home")
    apply_obj = get_object_or_404(RoleChangeApply, id=apply_id)
    if apply_obj.status != "pending":
        messages.warning(request, "This application has already been processed")
        return redirect("admin_audit_role")
    if request.method == "POST":
        operate = request.POST.get("operate")
        remark = request.POST.get("admin_remark", "")
        apply_obj.audit_admin = request.user
        apply_obj.admin_remark = remark
        if operate == "approve":
            apply_obj.status = "approved"
            apply_obj.user.role = apply_obj.target_role
            apply_obj.user.save()
            messages.success(request, "Approved successfully, user role updated")
        elif operate == "reject":
            apply_obj.status = "rejected"
            messages.success(request, "Application rejected")
        apply_obj.save()
    return redirect("admin_audit_role")

# 管理员用户列表不变
@login_required
def admin_all_user_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrator can access this page.")
        return redirect("home")
    user_queryset = UserModel.objects.all().order_by("id")
    paginator = Paginator(user_queryset, 20)
    page_num = request.GET.get("page", 1)
    page_data = paginator.get_page(page_num)
    return render(request, "manage/all_user_list.html", {"page": page_data})

# 管理员：所有用户提交邮件审核总列表
@login_required
def admin_email_audit_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrators can access audit page.")
        return redirect("home")
    all_audit = UserEmailAudit.objects.all().select_related("creator", "email_template").order_by("-submit_time")
    paginator = Paginator(all_audit, 15)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "manage/email_audit_list.html", {"page_data": page_data})

# 管理员审核单详情处理
@login_required
def audit_single_user_mail(request, audit_id):
    if not is_admin(request.user):
        messages.error(request, "Permission denied")
        return redirect("home")
    audit_obj = get_object_or_404(UserEmailAudit, id=audit_id)
    mail_tpl = audit_obj.email_template
    if request.method == "POST":
        action = request.POST.get("action")
        reject_note = request.POST.get("reject_note", "").strip()
        audit_obj.auditor = request.user
        audit_obj.audit_time = timezone.now()
        if action == "approve":
            audit_obj.status = "approved"
            mail_tpl.is_available = True
            mail_tpl.save()
            messages.success(request, "Approved, this email will appear in L2 training pool.")
        elif action == "reject":
            if not reject_note:
                messages.error(request, "Please fill in the rejection reason.")
                return redirect("audit_single_user_mail", audit_id=audit_id)
            audit_obj.status = "rejected"
            audit_obj.reject_note = reject_note
            # 驳回保持is_available=False，不进入训练池
            messages.success(request, "Rejected successfully, user can view your feedback.")
        audit_obj.save()
        return redirect("admin_email_audit_list")
    return render(request, "manage/email_audit_detail.html", {"audit": audit_obj, "mail": mail_tpl})