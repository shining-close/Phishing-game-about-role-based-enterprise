from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
import random


class UserConsentRecord(models.Model):
    participant_anon_id = models.CharField(max_length=64, verbose_name="Anonymous Participant ID")
    consent_datetime = models.DateTimeField(auto_now_add=True, verbose_name="Consent Submit Time")
    class Meta:
        verbose_name = "User Informed Consent Record"
        verbose_name_plural = "User Informed Consent Records"
    def __str__(self):
        return f"{self.participant_anon_id} | {self.consent_datetime.strftime('%Y-%m-%d %H:%M')}"

# User Main Model: Add L2 cumulative points and L3 unlock mark
import uuid

class UserModel(AbstractUser):
    ROLE_CHOICES = (
        ('hr', 'Human Resources'),
        ('finance', 'Finance Department'),
        ('it', 'IT Department'),
        ('admin', 'Administrator'),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name="Job Role",
        default="hr"
    )
    pre_test_score = models.FloatField(default=0.0)   # Average score of pre‑baseline test
    post_test_score = models.FloatField(default=0.0)  # Most recent training综合得分
    l2_total_points = models.IntegerField(default=0)  # L2 cumulative total points (for unlocking L3)
    unlock_l3 = models.BooleanField(default=False, verbose_name="Unlock L3 Training")    # True=unlock difficulty 3 training
    has_consented = models.BooleanField(default=False, verbose_name="Has signed consent form")
    
    # ===== New Addition: Anonymous Participant UUID =====
    anon_participant_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Anonymous Participant ID (Research Only)"
    )

    def __str__(self):
        return f"{self.username} | {self.get_role_display()}"

    # New: Automatically generate random UUID for new users
    def save(self, *args, **kwargs):
        # Generate 4-digit random number ID for new users
        if not self.pk and not self.anon_participant_id:
            # 0‑9999, pad with leading zeros if necessary, e.g., 0042
            self.anon_participant_id = f"{random.randint(0, 9999):04d}"
        super().save(*args, **kwargs)

    # Check if L3 can be unlocked: cumulative L2 points ≥ 30 automatically unlocks
    def check_unlock_l3(self):
        if self.l2_total_points >= 30 and not self.unlock_l3:
            self.unlock_l3 = True
            self.save()
        return self.unlock_l3

    @classmethod
    def create_superuser(cls, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return cls._create_user(username, email, password,** extra_fields)


# Pre-test answer record (Original L1, only baseline assessment, no simulation behavior)
class PreTestRecord(models.Model):
    JUDGEMENT_OUTCOME = (
        ('right', 'Correct judgment'),
        ('wrong', 'Wrong judgment'),
    )
    TEST_DIFF_CHOICES = (
        (1, "L1 Basic General Training"),
        (4, "T0 Baseline Pre-Test"),
        (5, "T1 Post-Training Test"),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    target_email = models.ForeignKey("EmailTemplateModel", on_delete=models.CASCADE)
    
    test_difficulty = models.IntegerField(choices=TEST_DIFF_CHOICES, default=1)
    judge_result = models.CharField(max_length=5, choices=JUDGEMENT_OUTCOME)
    confidence_score = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    operation_timestamp = models.DateTimeField(auto_now_add=True)
    scam_type_tag = models.CharField(max_length=50, blank=True)

    def __str__(self):
        diff_text = dict(self.TEST_DIFF_CHOICES)[self.test_difficulty]
        return f"{self.user.username} {diff_text} | {self.judge_result} Conf:{self.confidence_score}"


# Simulation training sessions (only L2 and L3 are available)
class TrainSession(models.Model):
    TRAIN_DIFFICULTY = (
        (2, "Level 2 Intermediate Training"),
        (3, "Level 3 Advanced Training"),
        (4, "T0 Baseline Pre‑Test"),
        (5, "T1 Post‑Training Result Test"),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    difficulty = models.IntegerField(choices=TRAIN_DIFFICULTY)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_score = models.IntegerField(default=0) 
    correct_identify = models.IntegerField(default=0, verbose_name="Correctly identify the number of phishing emails")
    wrong_identify = models.IntegerField(default=0, verbose_name="Wrongly report legitimate emails")
    pass_level2 = models.BooleanField(default=False, verbose_name="Whether L2 is passed, unlocking L3")

    def __str__(self):
        return f"{self.user.username} L{self.difficulty} Session {self.id}"

# Training behavior Log (All operations in L2/L3 simulation inbox)
class UserMailAction(models.Model):
    ACTION_CHOICES = [
        ("open_mail", "Open mail"),
        ("mark_suspicious", "Mark as suspicious phishing"),
        ("delete_mail", "Delete mail"),
        ("click_link", "Click link inside mail"),  # High-risk penalty
        ("report_phish", "Report phishing"),
        ("mark_legit", "Mark as legitimate mail"),
    ]
    session = models.ForeignKey(TrainSession, on_delete=models.CASCADE)
    mail = models.ForeignKey("Level2EmailTemplateModel", on_delete=models.CASCADE)
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    action_time = models.DateTimeField(auto_now_add=True)
    confidence = models.IntegerField(
        choices=[(1,"1"),(2,"2"),(3,"3"),(4,"4"),(5,"5")],
        null=True, blank=True,
        verbose_name="Judgment Confidence(1~5)"
    )

    def __str__(self):
        return f"{self.session.user.username} {self.action_type}"

# L1/T0/T1 Email Template Model
class EmailTemplateModel(models.Model):
    EMAIL_CATEGORY = (
        ('legit', 'Legitimate Email'),
        ('phish', 'Phishing Email'),
    )
    DEPARTMENT_TAGS = (
        ('hr', 'HR'),
        ('finance', 'Finance'),
        ('it', 'IT'),
    )
    TEMPLATE_SERIAL_CHOICES = (
        (1, "Template No.1"),
        (2, "Template No.2"),
        (3, "Template No.3"),
        (4, "Template No.4"),
        (5, "Template No.5"),
    )
    
    TEST_DIFF_CHOICES = (
        (1, "L1 Basic General Training"),
        (4, "T0 Baseline Pre-Test"),
        (5, "T1 Post-Training Test"),
    )
    test_difficulty = models.IntegerField(
        choices=TEST_DIFF_CHOICES,
        default=1,
        verbose_name="Test Stage (L1/T0/T1)"
    )

    email_title = models.CharField(max_length=200, verbose_name="Email Subject")
    email_content = models.TextField(verbose_name="Email Body Text")
    fake_link = models.CharField(max_length=300, blank=True, verbose_name="Phishing Fake URL")
    email_label = models.CharField(max_length=10, choices=EMAIL_CATEGORY, verbose_name="Email label")
    department = models.CharField(max_length=20, choices=DEPARTMENT_TAGS, verbose_name="Target Department")
    fraud_feature_description = models.TextField(blank=True, verbose_name="Deceptive scam features")
    risk_keywords = models.CharField(max_length=500, blank=True, verbose_name="Risk Keywords (split by comma)")
    template_serial = models.IntegerField(choices=TEMPLATE_SERIAL_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        diff_text = dict(self.TEST_DIFF_CHOICES)[self.test_difficulty]
        return f"[{diff_text} | {self.get_department_display()}] {self.email_title}"

    class Meta:
        verbose_name = "L1 / T0 / T1 Email Template"
        verbose_name_plural = "L1 / T0 / T1 Email Templates"

# Email Template for L2/L3 Training (Level 2 and Level 3 Fully Differentiated)
class Level2EmailTemplateModel(models.Model):
    EMAIL_CATEGORY = (
        ('legit', 'Legitimate Email'),
        ('phish', 'Phishing Email'),
    )
    DEPARTMENT_TAGS = (
        ('hr', 'HR'),
        ('finance', 'Finance'),
        ('it', 'IT'),
    )
    TRAIN_DIFFICULTY = (
        (2, "Level 2 Intermediate"),
        (3, "Level 3 Advanced"),
        (4, "T0 Baseline Pre‑Test"),
        (5, "T1 Post‑Training Result Test"),
    )
    
    TEMPLATE_FILE_CHOICES = [
        ("L2_1", "L2 Template 1"),
        ("L2_2", "L2 Template 2"),
        ("L2_3", "L2 Template 3"),
        ("L3_1", "L3 Template 1"),
        ("L3_2", "L3 Template 2"),
    ]
    SOURCE_CHOICES = [
        ("admin", "Created by Administrator"),
        ("user_submit", "Submitted by L3 User"),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="admin", verbose_name="Source of Template")
    is_available = models.BooleanField(default=False, verbose_name="Available for Training")

    sender = models.CharField(max_length=256)
    subject = models.CharField(max_length=256)

    content_1 = models.TextField(blank=True, null=True)
    
    link_text_1 = models.CharField(max_length=200, blank=True, null=True)
    url_1 = models.CharField(max_length=512, blank=True, null=True)

    content_2 = models.TextField(blank=True, null=True)
    link_text_2 = models.CharField(max_length=200, blank=True, null=True)
    url_2 = models.CharField(max_length=512, blank=True, null=True)

    content_3 = models.TextField(blank=True, null=True)
    link_text_3 = models.CharField(max_length=200, blank=True, null=True)
    url_3 = models.CharField(max_length=512, blank=True, null=True)

    content_4 = models.TextField(blank=True, null=True)
    link_text_4 = models.CharField(max_length=200, blank=True, null=True)
    url_4 = models.CharField(max_length=512, blank=True, null=True)

    difficulty_level = models.IntegerField(choices=TRAIN_DIFFICULTY, verbose_name="Training Difficulty")
    
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_FILE_CHOICES,
        verbose_name="Template File",
        help_text="Select corresponding template html file"
    )

    email_label = models.CharField(max_length=10, choices=EMAIL_CATEGORY, verbose_name="Email Type")
    department = models.CharField(max_length=50, choices=DEPARTMENT_TAGS, verbose_name="Target Department")
    scam_keywords = models.TextField(blank=True, verbose_name="Scam Keywords (comma separated)")
    analysis_description = models.TextField(verbose_name="Feedback Analysis Text")

    def save(self, *args, **kwargs):
        if self.pk is None:
            if self.source == "admin":
                self.is_available = True
            elif self.source == "user_submit":
                self.is_available = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[L{self.difficulty_level} {self.department}] {self.subject}"
    class Meta:
        verbose_name = "L2/L3 Training Email Template"
        verbose_name_plural = "L2/L3 Training Email Templates"

class AdminModel(models.Model):
    admin_user = models.OneToOneField(UserModel, on_delete=models.CASCADE)
    admin_access_key = models.CharField(max_length=100)

class RoleChangeApply(models.Model):
    APPLY_STATUS = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="role_applies")
    target_role = models.CharField(max_length=20, choices=UserModel.ROLE_CHOICES, verbose_name="Want to change to role")
    apply_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=APPLY_STATUS, default="pending")
    admin_remark = models.TextField(blank=True, verbose_name="Admin audit remark")
    audit_admin = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_records")
    def __str__(self):
        return f"{self.user.username} apply {self.target_role} | {self.status}"

class UserEmailAudit(models.Model):
    AUDIT_STATUS = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    creator = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="email_submits")
    email_template = models.OneToOneField(Level2EmailTemplateModel, on_delete=models.CASCADE, related_name="audit_record")
    status = models.CharField(max_length=12, choices=AUDIT_STATUS, default="pending")
    auditor = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="email_audit_tasks")
    reject_note = models.TextField(blank=True, null=True, verbose_name="Reject Reason")
    submit_time = models.DateTimeField(auto_now_add=True)
    audit_time = models.DateTimeField(null=True, blank=True)

    score_dept_match = models.FloatField(default=0, verbose_name="Department Matching Score(0-30)")
    score_social_engineer = models.FloatField(default=0, verbose_name="Social Engineering Score(0-30)")
    score_fake_tech = models.FloatField(default=0, verbose_name="Forgery Tech Score(0-25)")
    score_flaw = models.FloatField(default=0, verbose_name="Flaw Conceal Score(0-15)")
    total_score = models.FloatField(default=0, verbose_name="Total Score")
    level_grade = models.CharField(max_length=20, blank=True, verbose_name="Evaluation Grade")
    score_suggest = models.TextField(blank=True, verbose_name="Optimization Suggestions")

    class Meta:
        ordering = ["-submit_time"]
        verbose_name = "User Submitted Email Audit"
        verbose_name_plural = "User Submitted Email Audits"
    def __str__(self):
        return f"{self.creator.username} - {self.status} | {self.email_template.subject}"

class ExperimentSurvey(models.Model):
   
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="survey_records")
    submit_time = models.DateTimeField(auto_now_add=True, verbose_name="Submit Time")

    # Part1 Overall experience Likert 1-5
    q1_interface_clear = models.IntegerField(verbose_name="Q1 Interface Clear(1-5)")
    q2_operation_easy = models.IntegerField(verbose_name="Q2 Easy Operation(1-5)")
    q3_session_length_ok = models.IntegerField(verbose_name="Q3 Training Length Appropriate(1-5)")

    # Part2 Core Research Points of Gradient Difficulty
    q4_diff_help_improve = models.IntegerField(verbose_name="Q4 Progressive difficulty improves ability(1-5)")
    q5_multi_diff_better = models.IntegerField(verbose_name="Q5 Multi-level better than single difficulty(1-5)")
    q6_most_help_level = models.CharField(max_length=10, verbose_name="Q6 Most helpful level")
    q7_most_suitable_level = models.CharField(max_length=10, verbose_name="Q7 Best daily training level")
    q8_level_advantage_text = models.TextField(verbose_name="Q8 Advantages of L1/L2/L3")
    q9_difficulty_jump_suggest = models.TextField(verbose_name="Q9 Difficulty jump rationality & comment")

    # Part3 Customized email training by department
    q10_dept_email_match = models.IntegerField(verbose_name="Q10 Emails match my department scene(1-5)")
    q11_dept_train_useful = models.IntegerField(verbose_name="Q11 Dept training improves recognition(1-5)")
    q12_most_deceptive_dept = models.TextField(blank=True, null=True, verbose_name="Q12 Most like mail interface")
    q13_prefer_train_mode = models.CharField(max_length=10, verbose_name="Q13 Prefer L1 general / L2 dept")

    # Part4 T0基线 & T1后测
    q14_t0_t1_performance_diff = models.IntegerField(verbose_name="Q14 Obvious score difference T0-T1(1-5)")
    q15_test_reality = models.IntegerField(verbose_name="Q15 T0/T1 reflect real ability(1-5)")

    # Part5 Suggestions for System Optimization
    q16_optimize_priority = models.CharField(max_length=20, verbose_name="Q16 Most need optimize module")
    q17_add_email_scenario = models.TextField(verbose_name="Q17 Hope to add email scenarios")
    q18_rule_adjust_suggest = models.TextField(verbose_name="Q18 Suggestions on scoring/unlock rules")

    # Part6 Comprehensive evaluation
    q19_willing_reuse = models.IntegerField(verbose_name="Q19 Will to reuse this system(1-5)")
    q20_other_comments = models.TextField(blank=True, null=True, verbose_name="Q20 Extra comments")

    class Meta:
        verbose_name = "Experiment Questionnaire"
        verbose_name_plural = "Experiment Questionnaires"

class ConfigRuleModel(models.Model):
    TYPE_CHOICES = [
        ("dept_hr_legit", "HR Legitimate Business Keywords"),
        ("dept_hr_phish", "HR Phishing Inducement Keywords"),
        ("dept_finance_legit", "Finance Legitimate Business Keywords"),
        ("dept_finance_phish", "Finance Phishing Inducement Keywords"),
        ("dept_it_legit", "IT Legitimate Business Keywords"),
        ("dept_it_phish", "IT Phishing Inducement Keywords"),
        ("se_authority", "Social Engineering - Authority"),
        ("se_urgent", "Social Engineering - Urgent"),
        ("se_fear", "Social Engineering - Loss Threat"),
        ("se_benefit", "Social Engineering - Benefit Reward"),
        ("regex_sender", "Fake Sender Regex Rule"),
        ("regex_domain", "Fake Domain Keyword"),
        ("flaw_word", "Low‑level Obvious Phrase"),
        ("forbid_word", "Prohibited Sensitive Word"),
        ("trusted_domain", "Trusted Whitelisted Domain")
    ]

    rule_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Rule Category")
    content = models.CharField(max_length=500, verbose_name="Keyword / Regex Content")
    desc = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description Remark")

    class Meta:
        verbose_name = "Scoring Config Rule"
        verbose_name_plural = "Scoring Config Rules"
        ordering = ["rule_type"]

    def __str__(self):
        return f"{self.get_rule_type_display()} | {self.content}"

