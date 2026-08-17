from pathlib import Path

import pytest

from kernel.agent_message_bus import AgentMessageBus


def test_reporting_chain_allows_expected_directions(tmp_path: Path):
    bus = AgentMessageBus(tmp_path)
    bus.send(sender="user", recipient="ameer", body="راجع الموقع", kind="chat_command")
    bus.send(sender="ameer", recipient="design", body="حلل الواجهة", kind="delegation")
    bus.send(sender="design", recipient="ameer", body="تم التحليل", kind="worker_report")
    messages = bus.list()
    assert [item["sender"] for item in messages] == ["user", "ameer", "design"]
    assert bus.snapshot()["worker_direct_founder_contact"] is False


def test_worker_cannot_contact_founder_directly(tmp_path: Path):
    bus = AgentMessageBus(tmp_path)
    with pytest.raises(PermissionError, match="reporting_chain"):
        bus.send(sender="design", recipient="founder", body="تجاوز أمير")


def test_unknown_actor_is_rejected(tmp_path: Path):
    bus = AgentMessageBus(tmp_path)
    with pytest.raises(ValueError, match="unknown_actor"):
        bus.send(sender="unknown", recipient="ameer", body="رسالة")
