from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. 用户主模型：新增L2累计积分、L3解锁标记
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
    pre_test_score = models.FloatField(default=0.0)   # 前置基线测试平均分
    post_test_score = models.FloatField(default=0.0)  # 最近一次训练综合得分
    l2_total_points = models.IntegerField(default=0)  # L2累计总积分（解锁L3用）
    unlock_l3 = models.BooleanField(default=False, verbose_name="Unlock L3 Training")    # True=解锁难度3训练

    def __str__(self):
        return f"{self.username} | {self.get_role_display()}"

    # 判断是否可以进入L3：累计L2积分≥30自动解锁
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

# 2. 前置预测试答题记录（原L1，仅基线测评，无仿真行为）
class PreTestRecord(models.Model):
    JUDGEMENT_OUTCOME = (
        ('right', 'Correct judgment'),
        ('wrong', 'Wrong judgment'),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    target_email = models.ForeignKey("EmailTemplateModel", on_delete=models.CASCADE)
    judge_result = models.CharField(max_length=5, choices=JUDGEMENT_OUTCOME)
    confidence_score = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    operation_timestamp = models.DateTimeField(auto_now_add=True)
    scam_type_tag = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username} PreTest {self.judge_result}"

# 3. 仿真训练会话（只存L2、L3）
class TrainSession(models.Model):
    TRAIN_DIFFICULTY = (
        (2, "Level 2 Intermediate Training"),
        (3, "Level 3 Advanced Training"),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    difficulty = models.IntegerField(choices=TRAIN_DIFFICULTY)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_score = models.IntegerField(default=0) # 本次会话得分
    correct_identify = models.IntegerField(default=0, verbose_name="正确辨别钓鱼邮件数")
    wrong_identify = models.IntegerField(default=0, verbose_name="误举报正常邮件数")
    pass_level2 = models.BooleanField(default=False, verbose_name="是否通过L2，解锁L3")

    def __str__(self):
        return f"{self.user.username} L{self.difficulty} Session {self.id}"

# 4. 训练行为日志（L2/L3仿真收件箱所有操作）
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

    def __str__(self):
        return f"{self.session.user.username} {self.action_type}"

# 5. PreTest专属邮件模板（原难度1，仅前置测试）
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
        return f"[{self.get_department_display()}] PreTest Template | {self.email_title}"
    class Meta:
        verbose_name = "Pre-Test Email Template"
        verbose_name_plural = "Pre-Test Email Templates"

# 6. L2/L3 训练邮件模板（难度2、3完全区分）
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
    )
    # 新增模板选择列表，覆盖现有html文件
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
    # 新增：用户自定义链接显示文本
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
    
    # 修改template_type：绑定选择框，不允许为空 blank=False
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

# 附属模型不变
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

# L3用户提交邮件审核单
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

    # ============ 新增自动打分字段 ============
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