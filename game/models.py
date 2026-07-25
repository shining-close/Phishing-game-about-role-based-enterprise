from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. UserModel: extended Django user with job role field (HR / Finance / IT)
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

    pre_test_score = models.FloatField(default=0.0)
    post_test_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.username} | {self.get_role_display()}"

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

# 2. EmailTemplateModel: store labelled legitimate / phishing emails filtered by department
class EmailTemplateModel(models.Model):
    # Email Classification: Normal / Phishing
    EMAIL_CATEGORY = (
        ('legit', 'Legitimate Email'),
        ('phish', 'Phishing Email'),
    )

    # Departmental Permission Isolation：hr / finance / it
    DEPARTMENT_TAGS = (
        ('hr', 'HR'),
        ('finance', 'Finance'),
        ('it', 'IT'),
    )

    # Difficulty Classification L1/L2/L3
    DIFFICULTY_CHOICES = (
        (1, "Level 1 Basic"),
        (2, "Level 2 Intermediate"),
        (3, "Level 3 Advanced"),
    )

    # Serial numbers of 5 independent templates under the same difficulty level 1~5
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
    difficulty_level = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1, verbose_name="Difficulty Level")
    email_label = models.CharField(max_length=10, choices=EMAIL_CATEGORY, verbose_name="Email label")
    department = models.CharField(max_length=20, choices=DEPARTMENT_TAGS, verbose_name="Target Department")
    fraud_feature_description = models.TextField(blank=True, verbose_name="Deceptive scam features")
    risk_keywords = models.CharField(max_length=500, blank=True, verbose_name="Risk Keywords (split by comma)")

    template_serial = models.IntegerField(
        choices=TEMPLATE_SERIAL_CHOICES,
        verbose_name="Template Serial No.(1-5, match Lx_x.html)",
        default=1 
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """The background list clearly displays: Department - Difficulty - Template No. - Email Subject"""
        return f"[{self.get_department_display()}] L{self.difficulty_level} T{self.template_serial} | {self.email_title}"
    
    class Meta:
        verbose_name = "Training Email Template"
        verbose_name_plural = "Training Email Templates"

class Level2EmailTemplateModel(models.Model):
    sender = models.CharField(max_length=255, verbose_name="Sender")
    recipient = models.CharField(max_length=255, blank=True, verbose_name="Recipient")
    subject = models.CharField(max_length=255, verbose_name="Email Subject")

    content_1 = models.TextField(blank=True, verbose_name="Content Paragraph 1")
    url_1 = models.CharField(max_length=300, blank=True, verbose_name="URL 1")

    content_2 = models.TextField(blank=True, verbose_name="Content Paragraph 2")
    url_2 = models.CharField(max_length=300, blank=True, verbose_name="URL 2")

    content_3 = models.TextField(blank=True, verbose_name="Content Paragraph 3")
    url_3 = models.CharField(max_length=300, blank=True, verbose_name="URL 3")

    content_4 = models.TextField(blank=True, verbose_name="Content Paragraph 4")
    url_4 = models.CharField(max_length=300, blank=True, verbose_name="URL 4")

    difficulty_level = models.IntegerField(default=2, verbose_name="Difficulty Level")
    template_type = models.CharField(max_length=20, verbose_name="Template File", help_text="L2_1 / L2_2 / L2_3")

    email_label = models.CharField(
        max_length=10,
        choices=[("phish", "Phishing"), ("legit", "Legitimate")],
        verbose_name="Email Type"
    )
    department = models.CharField(max_length=50, verbose_name="Target Department")
    scam_keywords = models.TextField(blank=True, verbose_name="Scam Keywords (comma separated)")
    analysis_description = models.TextField(verbose_name="Feedback Analysis Text")

    def __str__(self):
        return f"[L2 {self.department}] {self.subject}"

    class Meta:
        verbose_name = "Level2 Training Template"
        verbose_name_plural = "Level2 Training Templates"

# 3. GameRecordModel: log all user interaction data for later quantitative analysis (RQ3)
class GameRecordModel(models.Model):
    JUDGEMENT_OUTCOME = (
        ('right', 'Correct judgment'),
        ('wrong', 'Wrong judgment'),
    )
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    target_email = models.ForeignKey(EmailTemplateModel, on_delete=models.CASCADE, null=True, blank=True)
    # 新增：关联L2高阶邮件模板
    target_l2_email = models.ForeignKey(Level2EmailTemplateModel, on_delete=models.CASCADE, null=True, blank=True)
    judge_result = models.CharField(max_length=5, choices=JUDGEMENT_OUTCOME)
    confidence_score = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    operation_timestamp = models.DateTimeField(auto_now_add=True)
    scam_type_tag = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username} | {self.judge_result}"

# 4. AdminModel: backend administrator account extension
class AdminModel(models.Model):
    admin_user = models.OneToOneField(UserModel, on_delete=models.CASCADE)
    admin_access_key = models.CharField(max_length=100)


# 5. Role Change Application Form
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