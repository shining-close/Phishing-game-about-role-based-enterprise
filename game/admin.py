from django.contrib import admin
from .models import UserModel, EmailTemplateModel, GameRecordModel, AdminModel, RoleChangeApply

@admin.register(UserModel)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "pre_test_score", "post_test_score")

@admin.register(EmailTemplateModel)
class EmailTemplateAdmin(admin.ModelAdmin):
    # 列表页展示：新增 template_serial 模板序号
    list_display = (
        "email_title",
        "department",
        "difficulty_level",
        "template_serial",  # 新增：1~5模板编号
        "email_label",
        "fake_link",
        "created_at"
    )
    # 侧边快速筛选栏
    list_filter = ("department", "difficulty_level", "template_serial", "email_label")
    # 编辑页表单字段，加入 template_serial
    fields = (
        "email_title",
        "email_content",
        "fake_link",
        "difficulty_level",
        "template_serial",  # 必须添加，否则后台看不到模板序号输入框
        "email_label",
        "department",
        "risk_keywords",
        "fraud_feature_description"
    )
    # 支持按标题搜索
    search_fields = ("email_title",)

@admin.register(GameRecordModel)
class GameRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "target_email", "judge_result", "confidence_score", "operation_timestamp")

@admin.register(AdminModel)
class AdminModelAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "admin_access_key")

@admin.register(RoleChangeApply)
class RoleApplyAdmin(admin.ModelAdmin):
    list_display = ("user", "target_role", "status", "apply_time", "audit_admin", "admin_remark")
