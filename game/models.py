from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. UserModel: extended Django user with job role field (HR / Finance / IT)
class UserModel(AbstractUser):
    # Enumeration of three enterprise job roles from research paper
    ROLE_CHOICES = (
        ('hr', 'Human Resources'),
        ('finance', 'Finance Department'),
        ('it', 'IT Department'),
    )
    # Assigned department role for role-separated training scenes
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Job Role")
    # Pre-test score before gamified training
    pre_test_score = models.FloatField(default=0.0)
    # Post-test score after gamified training
    post_test_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.username} | {self.get_role_display()}"

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
    email_title = models.CharField(max_length=200, verbose_name="Email Subject")
    email_content = models.TextField(verbose_name="Email Body Text")
    email_label = models.CharField(max_length=10, choices=EMAIL_CATEGORY)
    department = models.CharField(max_length=20, choices=DEPARTMENT_TAGS, verbose_name="Target Department")
    fraud_feature_description = models.TextField(blank=True, verbose_name="Deceptive scam features")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_department_display()}] {self.email_title}"

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