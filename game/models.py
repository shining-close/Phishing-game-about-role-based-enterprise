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
    # Label to distinguish normal mail and scam mail
    EMAIL_CATEGORY = (
        ('legit', 'Legitimate Email'),
        ('phish', 'Phishing Email'),
    )
    # Match department tags with user role for access isolation
    DEPARTMENT_TAGS = (
        ('hr', 'HR'),
        ('finance', 'Finance'),
        ('it', 'IT'),
    )

    DIFFICULTY_CHOICES = (
        (1, "Level 1 Basic"),
        (2, "Level 2 Intermediate"),
        (3, "Level 3 Advanced"),
    )
    email_title = models.CharField(max_length=200, verbose_name="Email Subject")
    email_content = models.TextField(verbose_name="Email Body Text")
    fake_link = models.CharField(max_length=300, blank=True, verbose_name="Phishing Fake URL")

    difficulty_level = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1, verbose_name="Difficulty Level")
    email_label = models.CharField(max_length=10, choices=EMAIL_CATEGORY)
    department = models.CharField(max_length=20, choices=DEPARTMENT_TAGS, verbose_name="Target Department")
    fraud_feature_description = models.TextField(blank=True, verbose_name="Deceptive scam features")
    created_at = models.DateTimeField(auto_now_add=True)
    risk_keywords = models.CharField(max_length=500, blank=True, verbose_name="Risk Keywords (split by comma)")

    def __str__(self):
        return f"[{self.get_department_display()}] L{self.difficulty_level} {self.email_title}"

# 3. GameRecordModel: log all user interaction data for later quantitative analysis (RQ3)
class GameRecordModel(models.Model):
    # Four classification results for user email judgement
    JUDGEMENT_OUTCOME = (
        ('TP', 'True Positive: Correctly identify phish'),
        ('TN', 'True Negative: Correctly identify normal mail'),
        ('FP', 'False Positive: Misjudge legit mail as phish'),
        ('FN', 'False Negative: Miss phishing email (critical risk)'),
    )
    # Foreign key link to trainee user
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    # Foreign key link to email template being judged
    target_email = models.ForeignKey(EmailTemplateModel, on_delete=models.CASCADE)
    judge_result = models.CharField(max_length=2, choices=JUDGEMENT_OUTCOME)
    # User self-reported confidence score (1 ~ 5 scale)
    confidence_score = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    operation_timestamp = models.DateTimeField(auto_now_add=True)
    scam_type_tag = models.CharField(max_length=50, blank=True)

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