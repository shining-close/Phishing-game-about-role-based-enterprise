from django.contrib import admin
from django import forms
# 移除GameRecordModel，新增3张训练日志表
from .models import (
    UserModel, EmailTemplateModel, Level2EmailTemplateModel,
    AdminModel, RoleChangeApply,
    PreTestRecord, TrainSession, UserMailAction
)

# 用户后台展示所有积分、解锁字段
@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = (
        "username", "email", "role",
        "pre_test_score", "post_test_score",
        "l2_total_points", "unlock_l3"
    )

# 预测试邮件模板（原L1）
# 预测试邮件模板（原L1）
@admin.register(EmailTemplateModel)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "email_title",
        "department",
        "template_serial",
        "email_label",
        "fake_link",
        "created_at"
    )
    list_filter = ("department", "template_serial", "email_label")
    fields = (
        "email_title",
        "email_content",
        "fake_link",
        "template_serial",
        "email_label",
        "department",
        "risk_keywords",
        "fraud_feature_description"
    )
    search_fields = ("email_title",)

# L2/L3共用训练邮件模板（删除强制difficulty=2限制，后台可自由选2/3）
@admin.register(Level2EmailTemplateModel)
class Level2EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ["subject", "department", "difficulty_level", "template_type", "email_label"]
    list_filter = ["department", "difficulty_level", "email_label"]
    search_fields = ["subject", "sender", "department"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "department":
            kwargs["widget"] = forms.Select(choices=[
                ("hr", "HR"),
                ("finance", "Finance"),
                ("it", "IT"),
            ])
        elif db_field.name == "template_type":
            kwargs["widget"] = forms.Select(choices=[
                ("L2_1", "L2_1"),
                ("L2_2", "L2_2"),
                ("L2_3", "L2_3"),
                ("L3_1", "L3_1"),
                ("L3_2", "L3_2"),
            ])
        elif db_field.name == "email_label":
            kwargs["widget"] = forms.Select(choices=[
                ("phish", "Phishing"),
                ("legit", "Legitimate")
            ])
        return super().formfield_for_dbfield(db_field, request,** kwargs)

# ========== 新增：预测试答题记录后台 ==========
@admin.register(PreTestRecord)
class PreTestRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "target_email", "judge_result", "confidence_score", "operation_timestamp")
    list_filter = ("judge_result",)
    search_fields = ("user__username", "target_email__email_title")

# ========== 新增：仿真训练会话后台 ==========
@admin.register(TrainSession)
class TrainSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "difficulty", "start_time", "end_time", "total_score")
    list_filter = ("difficulty",)
    search_fields = ("user__username",)

# ========== 新增：用户邮件行为日志后台 ==========
@admin.register(UserMailAction)
class UserMailActionAdmin(admin.ModelAdmin):
    list_display = ("session", "mail", "action_type", "action_time")
    list_filter = ("action_type", "session__difficulty")
    search_fields = ("session__user__username", "mail__subject")

# 管理员账号
@admin.register(AdminModel)
class AdminModelAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "admin_access_key")

# 角色变更申请
@admin.register(RoleChangeApply)
class RoleApplyAdmin(admin.ModelAdmin):
    list_display = ("user", "target_role", "status", "apply_time", "audit_admin", "admin_remark")

# ========== 废弃GameRecordModel 注释掉注册代码 ==========
# @admin.register(GameRecordModel)
# class GameRecordAdmin(admin.ModelAdmin):
#     list_display = ("user", "target_email", "judge_result", "confidence_score", "operation_timestamp")