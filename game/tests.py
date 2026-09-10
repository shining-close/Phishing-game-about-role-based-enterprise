# tests.py
from django.test import TestCase
from .models import (
    UserModel, Level2EmailTemplateModel, ConfigRuleModel,
    TrainSession, UserMailAction
)

class ModelOnlyTestCase(TestCase):
    

    def test_user_anon_id_auto_generated(self):
       
        u = UserModel.objects.create_user(
            username="t001",
            password="testpass123",
            role="finance"
        )
        self.assertIsNotNone(u.anon_participant_id)
        self.assertEqual(len(u.anon_participant_id),4)

    def test_check_unlock_l3_logic(self):
        
        u = UserModel.objects.create_user(username="t002", password="pw123", role="it")
        u.l2_total_points = 20
        u.unlock_l3 = False
        u.save()
        res = u.check_unlock_l3()
        self.assertFalse(res)

        u.l2_total_points = 35
        u.save()
        res2 = u.check_unlock_l3()
        self.assertTrue(res2)
        self.assertTrue(u.unlock_l3)

    def test_level2_template_admin_auto_available(self):
      
        tpl = Level2EmailTemplateModel.objects.create(
            source="admin",
            department="hr",
            difficulty_level=2,
            template_type="L2_1",
            email_label="legit",
            sender="hr@test.com",
            subject="Payroll update"
        )
        self.assertEqual(tpl.is_available, True)

    def test_level2_template_user_submit_auto_unavailable(self):
        
        tpl = Level2EmailTemplateModel.objects.create(
            source="user_submit",
            department="hr",
            difficulty_level=2,
            template_type="L2_1",
            email_label="phish",
            sender="fake@test.org",
            subject="Fake notice"
        )
        self.assertEqual(tpl.is_available, False)

    def test_config_rule_store(self):
     
        r = ConfigRuleModel.objects.create(
            rule_type="se_urgent",
            content="urgent"
        )
        self.assertEqual(r.content, "urgent")
