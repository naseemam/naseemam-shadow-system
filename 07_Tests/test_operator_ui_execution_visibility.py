from pathlib import Path


def _html() -> str:
    return (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")


def test_operator_ui_has_complete_rooms_and_execution_visibility():
    html = _html()
    for required in (
        "غرفة القيادة",
        "لوحة القيادة",
        "محادثة الأعمال",
        "المحادثة الشخصية",
        "سجل التنفيذ",
        "الموافقات النهائية",
        "تنفيذ فعلي موثّق",
        "أوافق وأنفذ",
        "أرفض",
        "معاينة ناتج البناء",
        "/ui/runtime",
        "/ask",
        "/friendly-chat",
        "/chat/approvals/",
    ):
        assert required in html


def test_business_and_personal_chat_are_separately_persisted():
    html = _html()
    assert "ameer.business.chat.v3" in html
    assert "ameer.personal.chat.v1" in html
    assert "localStorage" in html
    assert "محفوظة على هذا الجهاز" in html


def test_approval_controls_are_only_bound_to_business_messages():
    html = _html()
    assert "room==='business'?data.chat_approval:null" in html
    assert "const endpoint=room==='business'?'/ask':'/friendly-chat'" in html
    assert "owner.token" in html
