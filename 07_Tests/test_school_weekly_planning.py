from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import ameer_server
from kernel.school_operations import SchoolOperations


def test_weekly_plan_prioritizes_deadlines_and_flags_missing_inputs(tmp_path, monkeypatch):
    monkeypatch.delenv("AMEER_DATA_DIR", raising=False)
    school = SchoolOperations(tmp_path)
    school.add_task(
        "تحديث سجل متابعة الطالبات",
        category="student_follow_up",
        priority="normal",
        due_at="2026-09-02",
    )
    school.add_task(
        "إضافة شواهد ملف الإنجاز",
        category="achievement_portfolio",
        priority="high",
        missing_inputs="صور النشاط وشهادة الحضور",
    )
    school.add_task(
        "مراجعة قائمة التسليم",
        category="school_records",
        priority="low",
        due_at="2026-09-20",
    )

    plan = school.weekly_plan(today=date(2026, 9, 1))

    assert [item["title"] for item in plan["next_three"]] == [
        "تحديث سجل متابعة الطالبات",
        "إضافة شواهد ملف الإنجاز",
        "مراجعة قائمة التسليم",
    ]
    assert plan["deadlines"][0]["attention_flags"] == ["موعده خلال 1 يوم"]
    assert plan["missing_inputs"][0]["missing_inputs"] == "صور النشاط وشهادة الحضور"
    assert len(plan["categories"]["achievement_portfolio"]) == 1


def test_completing_school_task_removes_it_from_next_actions(tmp_path, monkeypatch):
    monkeypatch.delenv("AMEER_DATA_DIR", raising=False)
    school = SchoolOperations(tmp_path)
    task = school.add_task("إكمال سجل التسليم", category="school_records", priority="high")

    school.update_task(task["id"], {"status": "done"})

    assert school.weekly_plan(today=date(2026, 9, 1))["next_three"] == []
    assert school.dashboard()["completed_tasks"] == 1


def test_school_dashboard_api_creates_and_completes_responsibility(tmp_path, monkeypatch):
    monkeypatch.delenv("AMEER_DATA_DIR", raising=False)
    monkeypatch.setattr(ameer_server, "SCHOOL_OPERATIONS", SchoolOperations(tmp_path))
    client = TestClient(ameer_server.app)

    created = client.post("/school/tasks", json={
        "title": "تحديث قائمة الطالبات",
        "category": "student_follow_up",
        "priority": "high",
        "missing_inputs": "القائمة النهائية",
    })
    assert created.status_code == 201
    task_id = created.json()["task"]["id"]

    dashboard = client.get("/school/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["weekly_plan"]["next_three"][0]["title"] == "تحديث قائمة الطالبات"

    completed = client.patch(f"/school/tasks/{task_id}", json={"status": "done"})
    assert completed.status_code == 200
    assert client.get("/school/dashboard").json()["open_tasks"] == 0


def test_shadow_school_page_loads_live_weekly_dashboard_module():
    root = Path(__file__).resolve().parents[1]
    html = (root / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")
    module = (root / "09_Assets" / "web" / "modules" / "school.js").read_text(encoding="utf-8")

    for required in ("لوحة متابعة المدرسة", 'id="schoolDashboard"', "/modules/school.js"):
        assert required in html
    for required in (
        "/school/dashboard",
        "/school/tasks",
        "متابعة الطالبات",
        "السجلات والقوائم",
        "ملف الإنجاز",
        "الخطوات الثلاث التالية",
    ):
        assert required in module
