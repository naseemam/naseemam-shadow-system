import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.worker_runtime import worker_access_policy


def test_ameer_internal_authority_is_enabled_for_engineering():
    policy = worker_access_policy("engineering")
    assert policy["read"]["enabled"] is True
    assert policy["write"]["enabled"] is True
    assert policy["write"]["authority"] == "ameer"
    assert policy["write"]["user_approval_required"] is False
    assert policy["execute_internal"]["enabled"] is True
    assert policy["execute_internal"]["authority"] == "ameer"
    assert policy["execute_internal"]["user_approval_required"] is False


def test_external_work_is_delegated_to_ameer_not_founder():
    policy = worker_access_policy("engineering")
    assert policy["external_effect"]["enabled"] is True
    assert policy["external_effect"]["authority"] == "ameer"
    assert policy["external_effect"]["approval"] == "ameer_orchestrated_delete_publish_gate"


def test_workers_remain_orchestrated_by_ameer():
    policy = worker_access_policy("engineering")
    assert policy["cross_worker_access"] is False
    assert policy["can_kill_other_processes"] is False
    assert policy["can_modify_governance"] is False
