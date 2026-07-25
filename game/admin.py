from django.contrib import admin
from django import forms
from .models import UserModel, EmailTemplateModel, GameRecordModel, AdminModel, RoleChangeApply, Level2EmailTemplateModel

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

@admin.register(Level2EmailTemplateModel)
class Level2EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ["subject", "department", "template_type", "email_label"]
    search_fields = ["subject", "sender", "department"]

    # 页面上隐藏 difficulty_level，不让管理员编辑
    def get_exclude(self, request, obj=None):
        return ["difficulty_level"]

    # 保存时强制 difficulty_level = 2
    def save_model(self, request, obj, form, change):
        obj.difficulty_level = 2
        super().save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # 部门下拉选项
        if db_field.name == "department":
            kwargs["widget"] = forms.Select(choices=[
                ("HR", "HR"),
                ("Finance", "Finance"),
                ("IT", "IT"),
            ])
        # 模板文件下拉 L2_1 / L2_2 / L2_3
        elif db_field.name == "template_type":
            kwargs["widget"] = forms.Select(choices=[
                ("L2_1", "L2_1"),
                ("L2_2", "L2_2"),
                ("L2_3", "L2_3"),
            ])
        # 邮件类型下拉
        elif db_field.name == "email_label":
            kwargs["widget"] = forms.Select(choices=[
                ("phish", "Phishing"),
                ("legit", "Legitimate")
            ])
        return super().formfield_for_dbfield(db_field, request,** kwargs)


@admin.register(GameRecordModel)
class GameRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "target_email", "judge_result", "confidence_score", "operation_timestamp")

@admin.register(AdminModel)
class AdminModelAdmin(admin.ModelAdmin):
    list_display = ("admin_user", "admin_access_key")

@admin.register(RoleChangeApply)
class RoleApplyAdmin(admin.ModelAdmin):
    list_display = ("user", "target_role", "status", "apply_time", "audit_admin", "admin_remark")
