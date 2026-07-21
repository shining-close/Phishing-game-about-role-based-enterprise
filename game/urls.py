from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("inbox/", views.inbox_view, name="inbox"),

        # L1 训练入口
    path("train/l1/", views.train_level1_view, name="train_l1"),
    # L2 训练入口（复制L1逻辑，仅修改difficulty_level=2）
    path("train/l2/", views.train_level2_view, name="train_l2"),
    # L3 训练入口
    path("train/l3/", views.train_level3_view, name="train_l3"),
    # 通用答题页面（携带难度、模板ID）
    path("train/<int:level>/question/<int:tpl_id>/", views.train_question, name="train_question"),
    # 5题全部完成后的结束页面
    path("train/complete/", views.train_complete, name="train_complete"),

    # Game submission log interface
    path("game/submit/", views.submit_game_record, name="submit_record"),

    path("profile/", views.profile_center, name="profile"),
    path("profile/change-pwd/", views.change_password, name="change_pwd"),
    path("profile/error-record/", views.user_error_record, name="user_error_record"),
    path("profile/apply-role/", views.apply_change_role, name="apply_role"),
    
    # admin
    path("manage/role-audit/", views.admin_role_audit_list, name="admin_role_audit"),
    path("manage/role-audit/<int:apply_id>/deal/", views.deal_role_apply, name="deal_role_apply"),
    path("manage/all-user-list/", views.admin_all_user_list, name="admin_all_user_list"),
    path("manage/all-game-logs/", views.admin_all_game_logs, name="admin_all_game_logs"),



]