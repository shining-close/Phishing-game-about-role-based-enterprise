from django.urls import path
from . import views
urlpatterns = [
  
    path("", views.home_view, name="home"),
    path("consent/", views.consent_page, name="consent_page"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # ===================== L1 General Test =====================
    path("pretest/start/", views.pretest_start, name="pretest_start"),
    path("pretest/<int:tpl_id>/", views.pretest_question, name="pretest_question"),
    path("pretest/complete/", views.pretest_complete, name="pretest_complete"),
    # ===================== L2/L3 simulation inbox training routing =====================
    path("train/l2/", views.train_l2_inbox, name="train_l2"),
    path("train/l3/", views.train_l3_inbox, name="train_l3"),
    path("train/l3/editor/", views.level3_editor, name="level3_editor"),
    path("train/l3/submit-mail/", views.submit_user_created_mail, name="submit_user_created_mail"),
    path("train/action-save/", views.mail_action_save, name="mail_action_save"),
    path("train/finish/", views.finish_train_session, name="finish_train_session"),
    path("train/report/<int:session_id>/", views.train_report, name="train_report"),
    path("train/l2/mail/<int:mail_id>/", views.l2_mail_detail, name="l2_mail_detail"),
    path("debrief/", views.debrief_view, name="debrief"),
    # ==================== "Personal center related  ====================
    path("profile/", views.profile_center, name="profile"),
    path("profile/change-pwd/", views.change_password, name="change_password"),
    path("profile/error-logs/", views.user_error_records, name="user_error_records"),
    path("profile/error-logs/<int:action_id>/", views.error_record_detail, name="error_record_detail"),
    path("profile/apply-role/", views.apply_change_role, name="apply_role_change"),
    path("profile/my-submit-mails/", views.my_submit_mail_list, name="my_submit_mail_list"),
    path("profile/submit-mail-detail/<int:pk>/", views.user_submit_mail_detail, name="user_submit_mail_detail"),
    path("t0-baseline/", views.t0_baseline_inbox, name="t0_baseline"),
    path("t1-posttrain/", views.t1_posttrain_inbox, name="t1_posttrain"),
    # ===================== Administrator Backend =====================
    path("manage/role-audit/", views.admin_role_audit_list, name="admin_role_audit"),
    path("manage/role-audit/<int:apply_id>/deal/", views.deal_role_apply, name="deal_role_apply"),
    path("manage/all-user-list/", views.admin_all_user_list, name="admin_all_user_list"),
    path("manage/email-audit/", views.admin_email_audit_list, name="admin_email_audit_list"),
    path("manage/email-audit/<int:audit_id>/deal/", views.audit_single_user_mail, name="audit_single_user_mail"),
    path("survey/", views.experiment_survey, name="experiment_survey"),
]
