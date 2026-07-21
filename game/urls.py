from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("inbox/", views.inbox_view, name="inbox"),

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


        # ========== HR three ==========
    path("train/hr/l1/1/", views.hr_l1_1, name="hr_l1_1"),
    path("train/hr/l1/2/", views.hr_l1_2, name="hr_l1_2"),
    path("train/hr/l2/1/", views.hr_l2_1, name="hr_l2_1"),
    path("train/hr/l2/2/", views.hr_l2_2, name="hr_l2_2"),
    path("train/hr/l3/1/", views.hr_l3_1, name="hr_l3_1"),
    path("train/hr/l3/2/", views.hr_l3_2, name="hr_l3_2"),

    # ========== Finance ==========
    path("train/fin/l1/1/", views.fin_l1_1, name="fin_l1_1"),
    path("train/fin/l1/2/", views.fin_l1_2, name="fin_l1_2"),
    path("train/fin/l2/1/", views.fin_l2_1, name="fin_l2_1"),
    path("train/fin/l2/2/", views.fin_l2_2, name="fin_l2_2"),
    path("train/fin/l3/1/", views.fin_l3_1, name="fin_l3_1"),
    path("train/fin/l3/2/", views.fin_l3_2, name="fin_l3_2"),

    # ========== IT ==========
    path("train/it/l1/1/", views.it_l1_1, name="it_l1_1"),
    path("train/it/l1/2/", views.it_l1_2, name="it_l1_2"),
    path("train/it/l2/1/", views.it_l2_1, name="it_l2_1"),
    path("train/it/l2/2/", views.it_l2_2, name="it_l2_2"),
    path("train/it/l3/1/", views.it_l3_1, name="it_l3_1"),
    path("train/it/l3/2/", views.it_l3_2, name="it_l3_2"),
]