from pathlib import Path

from kernel.agent_operations import AgentOperations
from kernel.business_operations import BusinessOperations
from kernel.worker_runtime import worker_access_policy


def test_store_agent_routes_dream_al_nada_commands(tmp_path: Path):
    ops = AgentOperations(tmp_path)
    assert ops.detect("اعرض لوحة حلم الندى") == "store.dashboard"
    result = ops.execute_natural("store.dashboard", "اعرض لوحة حلم الندى")
    assert result["status"] == "completed"
    assert result["result"]["center"]["name"] == "مركز حلم الندى"
    assert set(result["result"]["modules"]) >= {"inventory", "employees", "bookings"}


def test_center_schema_supports_inventory_staff_and_bookings(tmp_path: Path):
    business = BusinessOperations(tmp_path)
    profile = business.center_profile()
    assert profile["name"] == "مركز حلم الندى"
    product = business.add_product("مادة اختبار", stock=2, reorder_level=1)
    employee = business.add_employee("موظف اختبار", role="مشرف")
    booking = business.create_booking("حجز اختبار", "2030-01-01T10:00:00Z", employee_id=employee["id"])
    assert product["stock"] == 2
    assert employee["role"] == "مشرف"
    assert booking["employee_id"] == employee["id"]


def test_store_agent_has_separate_center_scope():
    policy = worker_access_policy("store")
    assert policy["worker_id"] == "store"
    assert "04_Memory/dream_al_nada" in policy["read"]["allowed_paths"]
    assert policy["cross_worker_access"] is False
    assert policy["external_effect"]["enabled"] is True
    assert policy["external_effect"]["authority"] == "ameer"
    assert policy["external_effect"]["approval"] == "ameer_orchestrated_root_asset_creation_gate"
