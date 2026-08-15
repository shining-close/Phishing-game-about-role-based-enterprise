from django.contrib import admin
from django import forms
# Import and export
from import_export.admin import ImportExportModelAdmin
from .models import (
    UserModel, EmailTemplateModel, Level2EmailTemplateModel,
    AdminModel, RoleChangeApply,ConfigRuleModel,
    PreTestRecord, TrainSession, UserMailAction, UserConsentRecord, ExperimentSurvey
)
# Informed consent record: Remove the username and replace it with an anonymous ID
@admin.register(UserConsentRecord)
class UserConsentRecordAdmin(ImportExportModelAdmin):
    list_display = ("id", "participant_anon_id", "consent_datetime")
    readonly_fields = ("consent_datetime",)
    search_fields = ["participant_anon_id"]

# User management: Display anonymous participant ID
@admin.register(UserModel)
class UserModelAdmin(ImportExportModelAdmin):
    list_display = (
        "username", "anon_participant_id", "email", "role",
        "pre_test_score", "post_test_score",
        "l2_total_points", "unlock_l3", "has_consented"
    )
    search_fields = ["username", "anon_participant_id"]

# Add display, filtering and editing of test_difficulty to EmailTemplateModel
@admin.register(EmailTemplateModel)
class EmailTemplateAdmin(ImportExportModelAdmin):
    list_display = (
        "email_title",
        "department",
        "test_difficulty",
        "template_serial",
        "email_label",
        "fake_link",
        "created_at"
    )
    list_filter = ("department", "test_difficulty", "template_serial", "email_label")
    fields = (
        "email_title",
        "email_content",
        "fake_link",
        "template_serial",
        "email_label",
        "department",
        "test_difficulty",
        "risk_keywords",
        "fraud_feature_description"
    )
    search_fields = ("email_title",)

# ========== Revised L2/L3 Email Template Management (with user‑submitted review function) ==========
@admin.register(Level2EmailTemplateModel)
class Level2EmailTemplateAdmin(ImportExportModelAdmin):
    # List display: New source, enabled or not
    list_display = [
        "subject",
        "department",
        "difficulty_level",
        "source",
        "is_available",
        "template_type",
        "email_label"
    ]
    # Side filtering: You can separately filter user submissions/pending review
    list_filter = ["source", "is_available", "department", "difficulty_level", "email_label"]
    # Expand the search scope and support keyword‑based and text‑analysis‑based retrieval
    search_fields = ["subject", "sender", "department", "scam_keywords", "analysis_description"]

    # Batch review operation
    actions = ["batch_approve_user_submit", "batch_reject_user_submit"]

    # Batch approve: Set as available, enter the training pool
    def batch_approve_user_submit(self, request, queryset):
        queryset.update(is_available=True)
    batch_approve_user_submit.short_description = "Approved, enable this email (join the training pool)"

    # Batch reject: Keep unavailable, do not participate in training
    def batch_reject_user_submit(self, request, queryset):
        queryset.update(is_available=False)
    batch_reject_user_submit.short_description = "Rejected, disable this email (do not join the training pool)"

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

# Add "test" to the PreTestRecord_To list and filter, distinguish L1/T0/T1
@admin.register(PreTestRecord)
class PreTestRecordAdmin(ImportExportModelAdmin):
    list_display = ("user", "test_difficulty", "target_email", "judge_result", "confidence_score", "operation_timestamp")
    list_filter = ("test_difficulty", "judge_result")
    search_fields = ("user__username", "user__anon_participant_id", "target_email__email_title")

@admin.register(TrainSession)
class TrainSessionAdmin(ImportExportModelAdmin):
    list_display = ("user", "difficulty", "start_time", "end_time", "total_score")
    list_filter = ("difficulty",)
    search_fields = ("user__username", "user__anon_participant_id")
    actions = ["delete_selected"]
    
@admin.register(UserMailAction)
class UserMailActionAdmin(ImportExportModelAdmin):
    list_display = ("session", "mail", "action_type", "action_time")
    list_filter = ("action_type", "session__difficulty")
    search_fields = ("session__user__username", "session__user__anon_participant_id", "mail__subject")

@admin.register(AdminModel)
class AdminModelAdmin(ImportExportModelAdmin):
    list_display = ("admin_user", "admin_access_key")

@admin.register(RoleChangeApply)
class RoleChangeApplyAdmin(ImportExportModelAdmin):
    list_display = ("user", "target_role", "status", "apply_time", "audit_admin", "admin_remark")
    search_fields = ("user__username", "user__anon_participant_id")

@admin.register(ExperimentSurvey)
class ExperimentSurveyAdmin(ImportExportModelAdmin):
    list_display = ("user", "q6_most_help_level", "q13_prefer_train_mode", "q19_willing_reuse", "submit_time")
    list_filter = ("q6_most_help_level", "q13_prefer_train_mode", "q19_willing_reuse")
    search_fields = ("user__username", "user__anon_participant_id", "q8_level_advantage_text", "q18_rule_adjust_suggest")
    actions = ["delete_selected"]

@admin.register(ConfigRuleModel)
class ConfigRuleAdmin(ImportExportModelAdmin):
    list_display = ["rule_type", "content", "desc"]
    list_filter = ["rule_type"]
    search_fields = ["content", "desc"]
