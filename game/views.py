from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from functools import wraps
from .forms import RegisterForm, LoginForm, ChangePasswordForm, RoleApplyForm
from .models import (
    EmailTemplateModel, Level2EmailTemplateModel,ConfigRuleModel,
    PreTestRecord, TrainSession, UserMailAction,
    UserModel, RoleChangeApply, UserEmailAudit, UserConsentRecord, ExperimentSurvey
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

# ====================== cosent form ======================

def consent_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        # Only read the database tag to see if informed consent has been given
        if request.user.has_consented:
            return view_func(request, *args, **kwargs)
        else:
            return redirect("consent_page")
    return _wrapped_view

def consent_page(request):
    # Agreed to jump directly to registration
    if request.session.get("has_consented"):
        return redirect("register")
    if request.method == "POST":
        agree = request.POST.get("agree")
        # If the checkbox is not ticked, return an error message
        if agree != "on":
            messages.error(request, "Please tick the consent checkbox to continue.")
            return render(request, "consent.html")
        
        request.session["has_consented"] = True
        return redirect("register")
    return render(request, "consent.html")

def debrief_view(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in first.")
        return redirect("login")
    user = request.user

    # Judgment: Whether the post-experiment questionnaire has been submitted ExperimentSurvey
    survey_finished = ExperimentSurvey.objects.filter(user=user).exists()

    if not survey_finished:
        messages.error(request, "Debrief page is available only after you complete the post‑experiment questionnaire.")
        return redirect("profile")

    return render(request, "debrief.html")


# ====================== Log in, register and log out） ======================
def register_view(request):
    # No informed‑consent tag, forcing consent popup.
    if not request.session.get("has_consented"):
        return redirect("consent_page")
        
    if request.user.is_authenticated:
        return redirect("home")
    register_form = RegisterForm()
    if request.method == "POST":
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            new_user = register_form.save()
            new_user.has_consented = True
            new_user.save()
            
            # Use the automatically generated anonymous ID
            UserConsentRecord.objects.create(
                participant_anon_id = new_user.anon_participant_id
            )
            
            login(request, new_user)
            # Clear the consent session flag to prevent reuse
            del request.session["has_consented"]
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

# ====================== Home Page (Control button unlock status) ======================
@login_required
def home_view(request):
    user = request.user
    has_pretest = PreTestRecord.objects.filter(user=user).exists()
    can_l3 = user.unlock_l3
    l2_total = user.l2_total_points
    return render(request, "home.html", {
        "has_pretest": has_pretest,
        "can_l3": can_l3,
        "l2_total": l2_total,
        "user": user
    })

# ====================== L1 pretest_start ======================
@login_required
@consent_required
def pretest_start(request):
    print("==== ENTER pretest_start, user=", request.user.username, "consent=", request.user.has_consented)
    user_dept = request.user.role
    train_question_list = []
    for serial_num in [1,2,3,4,5]:
        serial_all_mail = EmailTemplateModel.objects.filter(
            department=user_dept,
            template_serial=serial_num,
            test_difficulty=1
        )
        mail_list = list(serial_all_mail)
        if len(mail_list) == 0:
            msg = f"L1 training template serial {serial_num} missing, contact admin."
            return render(request, "train/error_tip.html", {"msg": msg})
        pick_one = random.choice(mail_list)
        train_question_list.append(pick_one)
    random.shuffle(train_question_list)
    request.session["pretest_queue"] = [obj.id for obj in train_question_list]
    request.session["pretest_idx"] = 0
    return redirect("pretest_question", tpl_id=train_question_list[0].id)

@login_required
@consent_required
def pretest_question(request, tpl_id):
    user = request.user
    # Read the session queue
    pretest_queue = request.session.get("pretest_queue", None)
    pretest_idx = request.session.get("pretest_idx", 0)
    # There is no queue. Just go back to your personal center
    if not pretest_queue:
        messages.warning(request, "Training session not found, please restart Level1 training.")
        return redirect("home")
    # Retrieve the current question id
    current_tpl_id = pretest_queue[pretest_idx]
    email_tpl = get_object_or_404(EmailTemplateModel, id=current_tpl_id)
    diff = email_tpl.test_difficulty
    total_count = len(pretest_queue)
    current_num = pretest_idx + 1

    if request.method == "POST":
        # Submit answer: Fix! Compare the tags to generate right/wrong
        user_judge = request.POST.get("judge_result")
        conf = int(request.POST.get("confidence", 3))
        real_label = email_tpl.email_label
        res = "right" if user_judge == real_label else "wrong"

        PreTestRecord.objects.create(
            user=user,
            target_email=email_tpl,
            test_difficulty=diff,
            judge_result=res,
            confidence_score=conf
        )
        # Index + 1
        pretest_idx += 1
        request.session["pretest_idx"] = pretest_idx
        # Check if all questions are completed
        if pretest_idx >= len(pretest_queue):
            del request.session["pretest_queue"]
            del request.session["pretest_idx"]
            messages.success(request, "Level1 training completed! L2 is unlocked now.")
            return redirect("home")
        else:
            # Redirect to the next question
            next_id = pretest_queue[pretest_idx]
            return redirect("pretest_question", tpl_id=next_id)
    # GET: Render the current problem
    return render(request, "train/L1/base_normalemail.html", {
        "mail_list": [],
        "diff": diff,
        "current_num": current_num,
        "total_count": total_count,
        "template": email_tpl,
        "sub_template": f"train/L1/L1_{email_tpl.template_serial}.html",
        "all_config": ConfigRuleModel.objects.all()
    })

@login_required
@consent_required
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
    PreTestRecord.objects.create(
        user=user,
        target_email=email_obj,
        test_difficulty=email_obj.test_difficulty,
        judge_result=res,
        confidence_score=conf,
        scam_type_tag=scam_tag
    )
    current_idx = request.session.get("pretest_idx", 0)
    next_idx = current_idx + 1
    request.session["pretest_idx"] = next_idx
    queue = request.session["pretest_queue"]
    if next_idx >= len(queue):
        all_records = PreTestRecord.objects.filter(user=user)
        if all_records.exists():
            total_conf = sum(r.confidence_score for r in all_records)
            avg_conf = total_conf / all_records.count()
            user.pre_test_score = round(avg_conf, 2)
            user.save()
        del request.session["pretest_queue"]
        del request.session["pretest_idx"]
        return redirect("pretest_complete")
    return redirect("pretest_question", tpl_id=queue[next_idx])

@login_required
@consent_required
def pretest_complete(request):
    return render(request, "train/L1/pretest_complete.html", {})

# ---------------- The T0 benchmark test diff=4 ----------------
@login_required
@consent_required
def t0_baseline_inbox(request):
    user = request.user
    t0_already_done = PreTestRecord.objects.filter(user=user, test_difficulty=4).exists()
    if t0_already_done:
        messages.warning(request, "You have already completed T0 Baseline Test, cannot retake.")
        return redirect("profile")

    mail_all = list(EmailTemplateModel.objects.filter(
        department=user.role,
        test_difficulty=4
    ))
    if len(mail_all) < 10:
        msg = f"T0 test needs at least 10 unique email content templates, current: {len(mail_all)}"
        return render(request, "train/error_tip.html", {"msg": msg})

    # All 10 independent email contents with no duplicate content
    mail_list = random.sample(mail_all, k=10)
    request.session["pretest_queue"] = [obj.id for obj in mail_list]
    request.session["pretest_idx"] = 0
    first_mail = mail_list[0]

    return render(request, "train/L1/base_normalemail.html", {
        "diff": 4,
        "current_num": 1,
        "total_count": 10,
        "template": first_mail,
        "sub_template": f"train/L1/L1_{first_mail.template_serial}.html",
        "all_config": ConfigRuleModel.objects.all()
    })

# ---------------- The T1 post-training test diff=5 ----------------
@login_required
@consent_required
def t1_posttrain_inbox(request):
    user = request.user
    t1_already_done = PreTestRecord.objects.filter(user=user, test_difficulty=5).exists()
    if t1_already_done:
        messages.warning(request, "You have already completed T1 Post‑Training Test, cannot retake.")
        return redirect("profile")

    mail_all = list(EmailTemplateModel.objects.filter(
        department=user.role,
        test_difficulty=5
    ))
    if len(mail_all) < 10:
        msg = f"T1 test needs at least 10 unique email content templates, current: {len(mail_all)}"
        return render(request, "train/error_tip.html", {"msg": msg})

    mail_list = random.sample(mail_all, k=10)
    request.session["pretest_queue"] = [obj.id for obj in mail_list]
    request.session["pretest_idx"] = 0
    first_mail = mail_list[0]

    return render(request, "train/L1/base_normalemail.html", {
        "diff": 5,
        "current_num": 1,
        "total_count": 10,
        "template": first_mail,
        "sub_template": f"train/L1/L1_{first_mail.template_serial}.html",
        "all_config": ConfigRuleModel.objects.all()
    })

# ====================== L2 / L3 simulation inbox training ======================
@login_required
@consent_required
def train_l2_inbox(request):
    user = request.user
    # Block users who have not completed the pre-test
    if not PreTestRecord.objects.filter(user=user).exists():
        messages.error(request, "Complete Pre-Test first before training!")
        return redirect("pretest_start")
    # Create this training session with difficulty=2
    session = TrainSession.objects.create(user=user, difficulty=2)
    # Replace the old DomainWhitelist and read all configurations
    all_config = ConfigRuleModel.objects.all()
    # Pull the L2 emails of the current user's department: Randomly sort, with a maximum of 10 emails in one round of training
    mail_queryset = Level2EmailTemplateModel.objects.filter(
        department=user.role,
        difficulty_level=2,
        is_available=True  # Only load the available emails that have passed the review
    ).order_by("?")[:10]
 
    if not mail_queryset.exists():
        msg = "L2 training emails are empty, contact admin."
        return render(request, "train/error_tip.html", {"msg": msg})
    mail_list = list(mail_queryset)
    
    # Pass all_config to replace the old domain_list
    return render(request, "inbox.html", {
        "session": session,
        "mail_list": mail_list,
        "diff": 2,
        "all_config": all_config
    })


@login_required
@consent_required
def l2_mail_detail(request, mail_id):
    mail = get_object_or_404(Level2EmailTemplateModel, id=mail_id)
    # Get the session from the url parameter_id
    session_id = request.GET.get("session_id")
    session_obj = get_object_or_404(TrainSession, id=session_id, user=request.user)

    # template_type Data Inventory L2_1 / L2_2. Stitch the complete path together
    sub_template = f"train/L2/{mail.template_type}.html"
    return render(request, "train/L2/_mail_preview.html", {
        "template": mail,
        "sub_template": sub_template,
        "diff": session_obj.difficulty  
    })

# AJAX saves user operation behaviors (open / mark / delete / click link)
@login_required
@consent_required
def mail_action_save(request):
    if request.method != "POST":
        return JsonResponse({"code": 400, "msg": "Invalid request"})
    
    session_id = request.POST.get("session_id")
    mail_id = request.POST.get("mail_id")
    action_type = request.POST.get("action")
    # New acceptance confidence level has been added
    confidence = request.POST.get("confidence")
    
    # Parameter null value verification
    if not session_id or not mail_id or not action_type:
        return JsonResponse({"code": 400, "msg": "缺少参数"})
    try:
        session_obj = get_object_or_404(TrainSession, id=session_id, user=request.user)
        mail_obj = get_object_or_404(Level2EmailTemplateModel, id=mail_id)
        
        # Check if the same record already exists (to avoid duplicate records)
        existing_action = UserMailAction.objects.filter(
            session=session_obj,
            mail=mail_obj,
            action_type=action_type
        ).exists()
        
        if not existing_action:
            # Construct creation parameters
            create_kwargs = {
                "session": session_obj,
                "mail": mail_obj,
                "action_type": action_type
            }
            # Only T0(4)/T1(5) is stored in the confidence level
            if session_obj.difficulty in (4, 5) and confidence:
                create_kwargs["confidence"] = int(confidence)

            UserMailAction.objects.create(**create_kwargs)
        
        return JsonResponse({"code": 200, "msg": "success"})
    except Exception as e:
        print("操作保存异常：", str(e))
        return JsonResponse({"code": 500, "msg": str(e)})

# To conclude this training, calculate the total score, count the number of correct identifications, and automatically unlock L3
@login_required
@consent_required
def finish_train_session(request):
    if request.method != "POST":
        return redirect("train_l2")
    
    session_id = request.POST.get("session_id")
    train_session = get_object_or_404(TrainSession, id=session_id, user=request.user)
    user = train_session.user
    diff = train_session.difficulty  # Retrieve the current session difficulty
    
    all_actions = UserMailAction.objects.filter(session=train_session).select_related("mail")
    mail_final_judge = {}
    clicked_phish_mail_ids = set()
    clicked_legit_mail_ids = set() # Record the email ids that have clicked on normal links
    
    for act in all_actions.order_by("action_time"):
        if act.action_type == "click_link":
            if act.mail.email_label == "phish":
                clicked_phish_mail_ids.add(act.mail.id)
            else:
                # Normal email clicks will be saved to the collection and only count as one bonus point
                clicked_legit_mail_ids.add(act.mail.id)
        else:
            mail_final_judge[act.mail.id] = act
    
    score = 0
    max_total = 30
    correct_count = 0
    wrong_count = 0
    
    # 1. Score for handling reports/marking judgment
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
    
    # 2. Phishing links will be deducted points (only once per link)
    score -= len(clicked_phish_mail_ids) * 6
    # 3. For normal emails, click to get bonus points (only once per email, +2 per email)
    score += len(clicked_legit_mail_ids) * 2
    
    final_score = max(0, min(score, max_total))
    pass_level2 = final_score >= 30
    
    # Save the basic data of the session (for all difficulty levels)
    train_session.total_score = final_score
    train_session.end_time = timezone.now()
    train_session.correct_identify = correct_count
    train_session.wrong_identify = wrong_count
    train_session.pass_level2 = pass_level2
    train_session.save()
    if diff == 2:
        user.l2_total_points += final_score
        if pass_level2 and not user.unlock_l3:
            user.unlock_l3 = True
        user.save()
        user.check_unlock_l3()
    if diff in (4, 5):
        return redirect("debrief")
    else:
        return redirect("train_report", session_id=session_id)

# Training report page
@login_required
@consent_required
def train_report(request, session_id):
    session_obj = get_object_or_404(TrainSession, id=session_id, user=request.user)
    all_actions = UserMailAction.objects.filter(session=session_obj).select_related("mail").order_by("action_time")
    
    deducted_phish_mail = set()
    deducted_legit_mail = set() # Record the normal emails that have been added points
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
                if mail.id not in deducted_phish_mail:
                    delta = -6
                    total_minus += 6
                    deducted_phish_mail.add(mail.id)
                    reason = "First click of links in this phishing mail, deduct 6 points"
                else:
                    delta = 0
                    reason = "Repeated clicks on links of the same phishing mail, no repeated deduction"
            else:
                # The logic for adding points to normal email links
                if mail.id not in deducted_legit_mail:
                    delta = 2
                    total_add += 2
                    deducted_legit_mail.add(mail.id)
                    reason = "Clicked official trusted link in legitimate email, gain 2 bonus points"
                else:
                    delta = 0
                    reason = "Repeated clicks on legitimate mail link, no extra bonus"
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
    
    raw_score = total_add - total_minus
    final_score = max(0, min(raw_score, 30))
    return render(request, "train/report.html", {
        "session": session_obj,
        "detail_list": detail_list,
        "total_add": total_add,
        "total_minus": total_minus,
        "final_score": final_score  
    })


# ====================== L3 email creation and submission ======================
# Stop word list, filtering meaningless function words when splitting long keywords
# Stop word list, filtering meaningless function words when splitting long keywords
_STOP_WORDS = {
    "the", "a", "an", "of", "to", "in", "for", "on", "at", "and", "or",
    "is", "are", "was", "were", "be", "by", "with", "from", "within",
    "due", "all", "your", "you", "our", "will", "has", "have", "had",
    "this", "that", "it", "its", "as", "into", "via", "per", "can",
}

# 注释全局缓存变量，删除缓存逻辑
# _RULE_MAP_CACHE = None
def build_rule_map():
    # global _RULE_MAP_CACHE
    # if _RULE_MAP_CACHE is not None:
    #     return _RULE_MAP_CACHE
    all_rules = ConfigRuleModel.objects\
        .exclude(content__isnull=True)\
        .exclude(content="")\
        .only("rule_type", "content")
    rule_map = {}
    for item in all_rules:
        rt = item.rule_type.strip()
        word = item.content.strip()
        if not word:
            continue
        if rt not in rule_map:
            rule_map[rt] = []
        rule_map[rt].append(word)
    # _RULE_MAP_CACHE = rule_map
    return rule_map


# Keyword Intelligent matching tool function (Solving the problem of long phrases not hitting the target
def _keyword_hit(keyword, text):
    kw = keyword.lower().strip()
    if kw in text:
        return True

    words = [w.strip(".,!?;:()[]{}\"'") for w in kw.split()]
    core_words = [w for w in words if len(w) >= 4 and w not in _STOP_WORDS]
    for cw in core_words:
        if cw in text:
            return True
        if "-" in cw:
            parts = [p for p in cw if len(p) >= 3]
            if parts and all(p in text for p in parts):
                return True
    return False


@login_required
@consent_required
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

# L3 email editor page
@login_required
@consent_required
def level3_editor(request):
    user = request.user
    if not PreTestRecord.objects.filter(user=user).exists():
        messages.error(request, "Complete Pre‑Test first before creating emails.")
        return redirect("pretest_start")
    if not user.unlock_l3:
        messages.error(request, f"You need at least 30 L2 points to unlock Level3 creation, current: {user.l2_total_points}")
        return redirect("home")
    rule_map = build_rule_map()
    role = user.role.strip()
    dept_legit_key = f"dept_{role}_legit"
    dept_phish_key = f"dept_{role}_phish"
   
    dept_legit_words = rule_map.get(dept_legit_key, []) or []
    dept_phish_words = rule_map.get(dept_phish_key, []) or []
    se_groups = {
        "authority": rule_map.get("se_authority", []) or [],
        "urgent": rule_map.get("se_urgent", []) or [],
        "fear_loss": rule_map.get("se_fear", []) or [],
        "benefit": rule_map.get("se_benefit", []) or [],
    }
    flaw_words = rule_map.get("flaw_word", []) or []
    forbid_words = rule_map.get("forbid_word", []) or []
    fake_sender_keywords = rule_map.get("regex_sender", []) or []
    fake_domain_keywords = rule_map.get("regex_domain", []) or []
    return render(request, "train/L3/editor.html", {
        "user_dept": user.role,
        "dept_legit_words": dept_legit_words,
        "dept_phish_words": dept_phish_words,
        "se_groups": se_groups,
        "flaw_words": flaw_words,
        "forbid_words": forbid_words,
        "fake_sender_keywords": fake_sender_keywords,
        "fake_domain_keywords": fake_domain_keywords,
    })


# L3 Submit to create the email interface
@login_required
@consent_required
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
    email_label = request.POST.get("email_label", "")
    scam_keywords = request.POST.get("scam_keywords", "")
    analysis_desc = request.POST.get("analysis_description", "")
    diff = 2
    template_type = request.POST.get("template_type", "")
    dept = user.role
    source_type = "user_submit"

    # Form basic verification
    if not sender or not subject:
        messages.error(request, "Sender and Subject cannot be empty.")
        return redirect("level3_editor")
    if not template_type:
        messages.error(request, "You must select a template file.")
        return redirect("level3_editor")

    #Form basic verification
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
        difficulty_level=diff,
        template_type=template_type,
        email_label=email_label,
        department=dept,
        scam_keywords=scam_keywords,
        analysis_description=analysis_desc,
        source=source_type
    )
    audit_record = UserEmailAudit.objects.create(creator=user, email_template=new_mail)

    # Assemble text and link parameters
    content_list = [c1, c2, c3, c4]
    url_list = [u1, u2, u3, u4]
    rule_map = build_rule_map()

    # Debug the output on the console to check if the word library is loading normally
    print("=====Debug and output the scoring word bank=====")
    print("regex_sender:", rule_map.get("regex_sender", []))
    print("regex_domain:", rule_map.get("regex_domain", []))
    print("se_urgent:", rule_map.get("se_urgent", []))
    print("dept_it_phish:", rule_map.get("dept_it_phish", []))
    print("flaw_word:", rule_map.get("flaw_word", []))

    dept_legit_key = f"dept_{dept}_legit"
    dept_phish_key = f"dept_{dept}_phish"
    score_result = calc_phish_score(
        sender=sender,
        subject=subject,
        content_list=content_list,
        url_list=url_list,
        rule_map=rule_map,
        dept_key_legit=dept_legit_key,
        dept_key_phish=dept_phish_key
    )

    # Split scoring results
    s1 = score_result["s1_dept_match"]
    s2 = score_result["s2_social"]
    s3 = score_result["s3_camouflage"]
    s4 = score_result["s4_flaw"]
    total = score_result["total_score"]
    suggest_list = score_result["suggestions"]
    suggest_text = "\n".join(suggest_list) if suggest_list else "No optimization suggestions."

    # Rating determination
    if total >= 90:
        grade = "Excellent"
    elif total >= 70:
        grade = "Good"
    elif total >= 40:
        grade = "Normal"
    else:
        grade = "Poor"

    # Write the score sheet into the review form
    audit_record.score_dept_match = s1
    audit_record.score_social_engineer = s2
    audit_record.score_fake_tech = s3
    audit_record.score_flaw = s4
    audit_record.total_score = total
    audit_record.level_grade = grade
    audit_record.score_suggest = suggest_text
    audit_record.save()

    messages.success(request, "Your email draft has been submitted, waiting for administrator review.")
    return redirect("my_submit_mail_list")

# Core Automatic Scoring Function (Fixed Long phrase Matching BUG)
def calc_phish_score(sender, subject, content_list, url_list, rule_map, dept_key_legit, dept_key_phish):
    suggest_list = []
    full_text = " ".join([subject] + content_list).lower()

    # ========= S1 Departmental business matching score  0-30 =========
    dept_kw = [kw.lower() for kw in rule_map.get(dept_key_legit, [])]
    hit_dept = sum(1 for kw in dept_kw if _keyword_hit(kw, full_text))
    s1 = 30 if hit_dept >= 2 else int(15 * hit_dept)
    if hit_dept < 2:
        suggest_list.append(f"[Dept‑Match] Hit {hit_dept} official business keywords, need ≥2 for full 30pts")

    # ========= S2 Social Engineering Lure Score 0-30 (5 Categories) =========
    hit_cat = 0
    auth_list = [x.lower() for x in rule_map.get("se_authority", [])]
    urg_list = [x.lower() for x in rule_map.get("se_urgent", [])]
    loss_list = [x.lower() for x in rule_map.get("se_fear", [])]
    bene_list = [x.lower() for x in rule_map.get("se_benefit", [])]
    dept_phish_list = [x.lower() for x in rule_map.get(dept_key_phish, [])]

    if any(_keyword_hit(k, full_text) for k in auth_list): hit_cat += 1
    if any(_keyword_hit(k, full_text) for k in urg_list): hit_cat += 1
    if any(_keyword_hit(k, full_text) for k in loss_list): hit_cat += 1
    if any(_keyword_hit(k, full_text) for k in bene_list): hit_cat += 1
    if any(_keyword_hit(k, full_text) for k in dept_phish_list): hit_cat += 1

    s2 = min(hit_cat * 10, 30)
    if hit_cat < 5:
        suggest_list.append(f"[Social‑Eng] Hit {hit_cat}/5 lure categories, 10pts per category, max 30pts")

    # ========= The S3 camouflage technology is divided into 0/25  =========
    sender_fake = False
    sender_lower = sender.lower()
    sender_keywords = [sk.lower() for sk in rule_map.get("regex_sender", [])]
    for kw in sender_keywords:
        if kw in sender_lower:
            sender_fake = True
            break

    has_fake_url = False
    domain_keywords = [dk.lower() for dk in rule_map.get("regex_domain", [])]
    for raw_url in url_list:
        if not raw_url:
            continue
        url_low = raw_url.lower()
        for dk in domain_keywords:
            if dk in url_low:
                has_fake_url = True
                break
        if has_fake_url:
            break
    s3 = 25.0 if (sender_fake or has_fake_url) else 0.0
    if not sender_fake and not has_fake_url:
        all_url_empty = all(not u for u in url_list)
        if all_url_empty:
            suggest_list.append("[Camouflage] No phishing links filled")
        else:
            suggest_list.append("[Camouflage] Neither sender nor url contains camouflage keywords")

    # ========= For S4, low-level flaws will result in a deduction of 0 to 15 points =========
    flaw_total = 0
    flaw_kw = [fw.lower() for fw in rule_map.get("flaw_word", [])]
    for para in content_list:
        pl = para.lower()
        for fw in flaw_kw:
            if fw in pl:
                flaw_total += 1
    s4 = max(0, 15 - flaw_total * 3)
    if flaw_total > 0:
        suggest_list.append(f"[Flaw‑Conceal] Hit {flaw_total} low‑level flaw words, each deduct 3pts")

    total = s1 + s2 + s3 + s4
    return {
        "s1_dept_match": s1,
        "s2_social": s2,
        "s3_camouflage": s3,
        "s4_flaw": s4,
        "total_score": round(total, 1),
        "suggestions": suggest_list
    }

# ====================== Personal Center, Change Password, Role Application, Administrator Backend ======================
def is_admin(user):
    return user.is_authenticated and user.role == "admin"


@login_required
@consent_required
def profile_center(request):
    user = request.user
    # Check if there are any pending role applications
    has_pending_apply = RoleChangeApply.objects.filter(user=user, status="pending").exists()

    # T0 Benchmark Test difficulty=4, T1 Achievement Test difficulty=5
    has_finish_t0 = TrainSession.objects.filter(user=user, difficulty=4, end_time__isnull=False).exists()
    has_finish_t1 = TrainSession.objects.filter(user=user, difficulty=5, end_time__isnull=False).exists()

    user_has_survey = user.survey_records.exists()

    return render(request, "profile/profile.html", {
        "user": user,
        "has_pending_apply": has_pending_apply,
        "role_list": UserModel.ROLE_CHOICES,
        "has_finish_t0": has_finish_t0,
        "has_finish_t1": has_finish_t1,
        "user_has_survey": user_has_survey,
    })


@login_required
@consent_required
def change_password(request):
    user = request.user
    form = ChangePasswordForm()
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            from django.contrib.auth.hashers import check_password, make_password
            old_pwd = form.cleaned_data["old_password"]
            new_pwd = form.cleaned_data["new_password"]
            if not check_password(old_pwd, user.password):
                messages.error(request, "Original password is incorrect")
            else:
                user.password = make_password(new_pwd)
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("profile")
    return render(request, "profile/change_pwd.html", {"form": form})

# Submit a role switch application (use RoleApplyForm to automatically filter the current role)
@login_required
@consent_required
def apply_change_role(request):
    user = request.user
    # Repeated submission of applications awaiting review is prohibited
    if RoleChangeApply.objects.filter(user=user, status="pending").exists():
        messages.error(request, "You have a pending role change application, cannot submit again.")
        return redirect("personal_center")

    form = RoleApplyForm(user=user)
    # Filter out the current role and admin role from the list of all roles
    all_roles = list(UserModel.ROLE_CHOICES)
    # Remove the admin option
    all_roles = [(k,v) for k,v in all_roles if k != "admin"]
    # Then eliminate your current role
    filtered_roles = [(k,v) for k,v in all_roles if k != user.role]

    if request.method == "POST":
        form = RoleApplyForm(request.POST, user=user)
        if form.is_valid():
            apply_obj = form.save(commit=False)
            apply_obj.user = user
            apply_obj.save()
            messages.success(request, "Role change application submitted, waiting for administrator review.")
            return redirect("personal_center")
    # Pass the filtered role list to the template
    return render(request, "profile/apply_role.html", {"role_list": filtered_roles})

# List of user wrong‑answer deduction records: 10 items per page, only the latest deduction operation is retained for the same email
@login_required
@consent_required
def user_error_records(request):
    from django.db.models import Max, OuterRef, Subquery, Q
    user = request.user
    # Subquery: The latest operation ID of each email in the current user's [All training Sessions]
    latest_action_sub = UserMailAction.objects.filter(
        session__user=user,
        mail=OuterRef("mail")
    ).values("mail").annotate(max_act_id=Max("id")).values("max_act_id")

    # Step 1: Filter out the latest operation for each email
    base_qs = UserMailAction.objects.filter(id__in=Subquery(latest_action_sub))

    # Step 2: Only retain score deduction operations
    error_actions = base_qs.filter(
        Q(action_type="report_phish", mail__email_label="legit")
        | Q(action_type="mark_legit", mail__email_label="phish")
        | Q(action_type="click_link", mail__email_label="phish")
    ).select_related("mail", "session").order_by("-action_time")

    paginator = Paginator(error_actions, 10)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "profile/error_record_list.html", {"page_data": page_data})

# List of user wrong‑answer deduction records: 10 items per page, only the latest deduction operation is retained for the same email
@login_required
@consent_required
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

# Users view all the pending or reviewed emails they have submitted
@login_required
@consent_required
def my_submit_mail_list(request):
    user = request.user
    audit_list = UserEmailAudit.objects.filter(creator=user).select_related("email_template")
    paginator = Paginator(audit_list, 10)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "profile/my_submit_mails.html", {"page_data": page_data})

@login_required
@consent_required
def user_submit_mail_detail(request, pk):
    # You can only view the review form you have submitted to prevent overstepping your authority
    audit_record = get_object_or_404(UserEmailAudit, pk=pk, creator=request.user)
    mail = audit_record.email_template
    return render(request, "profile/user_submit_mail_detail.html", {
        "record": audit_record,
        "mail": mail
    })

# ====================== Administrator Role Audit ======================
@login_required
@consent_required
def admin_role_audit_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrators can access this page")
        return redirect("home")
    all_apply = RoleChangeApply.objects.select_related("user").order_by("-apply_time")
    return render(request, "manage/role_audit_list.html", {"apply_list": all_apply})

@login_required
@consent_required
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

# Administrator user list remains unchanged
@login_required
@consent_required
def admin_all_user_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrator can access this page.")
        return redirect("home")
    user_queryset = UserModel.objects.all().order_by("id")
    paginator = Paginator(user_queryset, 20)
    page_num = request.GET.get("page", 1)
    page_data = paginator.get_page(page_num)
    return render(request, "manage/all_user_list.html", {"page": page_data})

# Administrator: List of all user-submitted email audits
@login_required
@consent_required
def admin_email_audit_list(request):
    if not is_admin(request.user):
        messages.error(request, "Only administrators can access audit page.")
        return redirect("home")
    all_audit = UserEmailAudit.objects.all().select_related("creator", "email_template").order_by("-submit_time")
    paginator = Paginator(all_audit, 15)
    page = request.GET.get("page", 1)
    page_data = paginator.get_page(page)
    return render(request, "manage/email_audit_list.html", {"page_data": page_data})

# Administrator: Detail page for reviewing a single user email audit
@login_required
@consent_required
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
            messages.success(request, "Rejected successfully, user can view your feedback.")
        audit_obj.save()
        return redirect("admin_email_audit_list")
    return render(request, "manage/email_audit_detail.html", {"audit": audit_obj, "mail": mail_tpl})

@login_required
def experiment_survey(request):
    # Each person is limited to submitting the questionnaire only once
    already_submit = ExperimentSurvey.objects.filter(user=request.user).exists()
    if already_submit:
        messages.info(request, "You have already submitted the questionnaire, thank you for your feedback!")
        return redirect("profile")
    if request.method == "POST":
        ExperimentSurvey.objects.create(
            user=request.user,
            # Part1
            q1_interface_clear=int(request.POST["q1"]),
            q2_operation_easy=int(request.POST["q2"]),
            q3_session_length_ok=int(request.POST["q3"]),
            # Part2
            q4_diff_help_improve=int(request.POST["q4"]),
            q5_multi_diff_better=int(request.POST["q5"]),
            q6_most_help_level=request.POST["q6"],
            q7_most_suitable_level=request.POST["q7"],
            q8_level_advantage_text=request.POST["q8"],
            q9_difficulty_jump_suggest=request.POST["q9"],
            # Part3
            q10_dept_email_match=int(request.POST["q10"]),
            q11_dept_train_useful=int(request.POST["q11"]),
            q12_most_deceptive_dept=request.POST["q12"],
            q13_prefer_train_mode=request.POST["q13"],
            # Part4
            q14_t0_t1_performance_diff=int(request.POST["q14"]),
            q15_test_reality=int(request.POST["q15"]),
            # Part5
            q16_optimize_priority=request.POST["q16"],
            q17_add_email_scenario=request.POST["q17"],
            q18_rule_adjust_suggest=request.POST["q18"],
            # Part6
            q19_willing_reuse=int(request.POST["q19"]),
            q20_other_comments=request.POST.get("q20", "")
        )
        messages.success(request, "Questionnaire submitted successfully! Thank you for your support.")
        # After submitting the questionnaire, directly jump to the unblinding page
        return redirect("debrief")
    return render(request, "survey.html")
