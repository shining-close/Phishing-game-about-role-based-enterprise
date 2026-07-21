from django.contrib import admin
from .models import UserModel, EmailTemplateModel, GameRecordModel, AdminModel, RoleChangeApply

@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "pre_test_score", "post_test_score")

@admin.register(EmailTemplateModel)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("email_title", "department", "difficulty_level", "email_label", "fake_link", "created_at")
    fields = (
        "email_title",
        "email_content",
        "fake_link",
        "difficulty_level",
        "email_label",
        "department",
        "risk_keywords",
        "fraud_feature_description"
    )

@admin.register(GameRecordModel)
class GameRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "target_email", "judge_result", "confidence_score", "operation_timestamp")

@admin.register(AdminModel)
class AdminModelAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "admin_access_key")

@admin.register(RoleChangeApply)
class RoleApplyAdmin(admin.ModelAdmin):
    list_display = ("user", "target_role", "status", "apply_time", "audit_admin", "admin_remark")
