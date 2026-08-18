from pathlib import Path


def _html() -> str:
    return (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")


def test_shadow_system_has_the_approved_information_architecture():
    html = _html()
    for required in (
        "نظام الظل",
        "المحادثة الودية",
        "محادثة الأعمال",
        "متابعة العملاء",
        "نسخة إشرافية · متجر حلم الندى",
        "حلم الندى",
        "موقع حلم الندى الأم",
        "برنامج إدارة حلم الندى",
        "حالة مشروع حلم الندى",
        "رابط وإدارة متجر حلم الندى",
        "المدرسة",
        "التداول",
        "موقع التداول",
        "لوحة التداول",
        "بوت التداول",
        "الاستراتيجيات",
        "الصفقات وسجل الأوامر",
        "الأداء والمخاطر",
        "إعدادات التداول",
        "الإدارة الشاملة",
    ):
        assert required in html


def test_chat_rooms_and_approval_controls_are_wired_to_correct_routes():
    html = _html()
    for required in (
        "/friendly-chat",
        "/ask",
        "/chat/approvals/",
        "أوافق وأنفذ",
        "أرفض",
        "room==='business'?'/ask':'/friendly-chat'",
        "room==='business'?d.chat_approval:null",
    ):
        assert required in html


def test_shadow_ui_uses_live_operational_data_and_separate_local_history():
    html = _html()
    for required in (
        "/ui/runtime",
        "/workers/runtime",
        "/center/dashboard",
        "/center/customers",
        "shadow.business.v1",
        "shadow.friendly.v1",
        "localStorage",
    ):
        assert required in html
