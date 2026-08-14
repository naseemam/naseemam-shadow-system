from pathlib import Path


def test_operator_ui_keeps_history_and_shows_execution_evidence():
    html = (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")

    assert "ameer.operator.ui.v2" in html
    assert "إيصال التنفيذ الفعلي" in html
    assert "بوابة موافقة نهائية" in html
    assert "execution_trace" in html
    assert "agent_action" in html
    assert "approval_id" in html
    assert "localStorage" in html
    assert "الكلام وحده لن يُحسب إنجازًا" in html
