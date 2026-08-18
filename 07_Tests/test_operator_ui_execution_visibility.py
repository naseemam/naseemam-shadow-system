from pathlib import Path


def test_operator_ui_is_more_than_ephemeral_chat():
    html = (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")

    assert "مركز التشغيل التنفيذي" in html
    assert "سجل التنفيذ" in html
    assert "الموافقات النهائية" in html
    assert "محادثة الأعمال" in html
    assert "تنفيذ فعلي موثّق" in html
    assert "أوافق وأنفذ" in html
    assert "/ui/runtime" in html
    assert "/ask" in html
    assert "/chat/approvals/" in html
    assert "execution_evidence" in html


def test_chat_survives_reload_on_same_device():
    html = (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")

    assert "ameer.operator.chat.v2" in html
    assert "localStorage" in html
    assert "محفوظة على هذا الجهاز" in html
