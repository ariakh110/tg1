from unittest.mock import patch

from django.test import TestCase

from .ai import _build_system_prompt
from .models import AssistantConversation, AssistantSettings
from .tools import capture_lead, execute_tool


class CaptureLeadValidationTests(TestCase):
    def setUp(self):
        self.conv = AssistantConversation.objects.create(session_key="t-cap")

    def test_rejects_invalid_phone(self):
        res = capture_lead(self.conv, name="حسن رضایی", phone="0912")
        self.assertFalse(res["ok"])
        self.conv.refresh_from_db()
        self.assertEqual(self.conv.lead_phone, "")

    def test_requires_name(self):
        res = capture_lead(self.conv, name="", phone="09120000000")
        self.assertFalse(res["ok"])

    def test_accepts_and_normalizes(self):
        # شمارهٔ بین‌المللی باید به 09... نرمال شود.
        res = capture_lead(self.conv, name="حسن رضایی", phone="+98 912 000 0000")
        self.assertTrue(res["ok"], res)
        self.conv.refresh_from_db()
        self.assertEqual(self.conv.lead_phone, "09120000000")
        self.assertEqual(self.conv.lead_name, "حسن رضایی")


class LeadGateTests(TestCase):
    def setUp(self):
        self.conv = AssistantConversation.objects.create(session_key="t-gate")

    def test_strict_gate_blocks_price_without_phone(self):
        res = execute_tool("get_price_quote", {"product_id": 1}, self.conv, lead_gate="strict")
        self.assertTrue(res.get("gated"))

    def test_price_allowed_after_phone_captured(self):
        self.conv.lead_phone = "09120000000"
        res = execute_tool("get_price_quote", {"product_id": 999999}, self.conv, lead_gate="strict")
        self.assertNotIn("gated", res)  # دیگر گیت نمی‌خورد (محصول نیست، ولی منع نشده)

    def test_off_mode_never_gates(self):
        res = execute_tool("get_price_quote", {"product_id": 999999}, self.conv, lead_gate="off")
        self.assertNotIn("gated", res)


class SystemPromptLeadBlockTests(TestCase):
    def setUp(self):
        self.cfg = AssistantSettings.load()
        self.conv = AssistantConversation.objects.create(session_key="t-prompt")

    def test_soft_mode_adds_persuasion_block(self):
        self.cfg.lead_capture_mode = AssistantSettings.LEAD_SOFT
        prompt = _build_system_prompt(self.cfg, [], self.conv)
        self.assertIn("نام و نام‌خانوادگی", prompt)

    def test_strict_mode_adds_gating_rule(self):
        self.cfg.lead_capture_mode = AssistantSettings.LEAD_STRICT
        prompt = _build_system_prompt(self.cfg, [], self.conv)
        self.assertIn("قانونِ اجباری", prompt)

    def test_off_mode_has_no_block(self):
        self.cfg.lead_capture_mode = AssistantSettings.LEAD_OFF
        prompt = _build_system_prompt(self.cfg, [], self.conv)
        self.assertNotIn("اولویتِ بالا", prompt)

    def test_already_captured_skips_asking(self):
        self.cfg.lead_capture_mode = AssistantSettings.LEAD_STRICT
        self.conv.lead_phone = "09120000000"
        prompt = _build_system_prompt(self.cfg, [], self.conv)
        self.assertIn("قبلاً ثبت شده", prompt)
