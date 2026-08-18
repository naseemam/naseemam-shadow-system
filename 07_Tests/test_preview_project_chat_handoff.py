from pathlib import Path


def test_project_preview_hands_work_to_business_chat():
    source = (Path(__file__).resolve().parents[1] / "ameer_server.py").read_text(encoding="utf-8")
    start = source.index("PROJECT_ACTION_BAR")
    end = source.index("@app.get('/preview/projects/{slug}'", start)
    action_bar = source[start:end]

    assert "محادثة الأعمال" in action_bar
    assert "المحادثة الشخصية" in action_bar
    assert "/?intent=" in action_bar
    assert "#business" in action_bar
    assert "بطاقة المحادثة" in action_bar
    assert "/approvals" not in action_bar
    assert "/agent/delegate" not in action_bar
