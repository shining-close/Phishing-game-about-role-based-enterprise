from django.urls import path
from . import views

urlpatterns = [
    # 基础公共页面（保留不变）
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # path("inbox/", views.inbox_view, name="inbox"),

    # ===================== 新增：前置预测试 PreTest（原L1） =====================
    path("pretest/start/", views.pretest_start, name="pretest_start"),
    path("pretest/<int:tpl_id>/", views.pretest_question, name="pretest_question"),
    path("pretest/complete/", views.pretest_complete, name="pretest_complete"),

    # ===================== 新增：L2/L3 仿真收件箱训练路由 =====================
    path("train/l2/", views.train_l2_inbox, name="train_l2"),
    path("train/l3/", views.train_l3_inbox, name="train_l3"),
    # AJAX提交用户邮件操作行为
    path("train/action-save/", views.mail_action_save, name="mail_action_save"),
    # 结束本次训练、结算积分
    path("train/finish/", views.finish_train_session, name="finish_train_session"),
    # 训练行为报告页面
    path("train/report/<int:session_id>/", views.train_report, name="train_report"),
    # 邮件概览
    path("train/l2/mail/<int:mail_id>/", views.l2_mail_detail, name="l2_mail_detail"),

    # ==================== 个人中心相关 ====================
    path("profile/", views.profile_center, name="profile"),
    path("profile/change-pwd/", views.change_password, name="change_password"),
    path("profile/error-logs/", views.user_error_records, name="user_error_records"),
    path("profile/error-logs/<int:action_id>/", views.error_record_detail, name="error_record_detail"),
    path("profile/apply-role/", views.apply_change_role, name="apply_role_change"),

    # ===================== 管理员后台（保留有效路由） =====================
    path("manage/role-audit/", views.admin_role_audit_list, name="admin_role_audit"),
    path("manage/role-audit/<int:apply_id>/deal/", views.deal_role_apply, name="deal_role_apply"),
    path("manage/all-user-list/", views.admin_all_user_list, name="admin_all_user_list"),
]