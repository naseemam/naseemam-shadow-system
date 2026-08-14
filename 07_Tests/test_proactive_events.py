from pathlib import Path

from kernel.proactive_events import ProactiveEventStore


def test_proactive_events_persist_and_count_unread(tmp_path: Path):
    store = ProactiveEventStore(tmp_path)
    store.emit("execution_completed", "أنجزت مهمة", "تم تغيير ملفين", severity="success")
    assert store.unread_count() == 1

    again = ProactiveEventStore(tmp_path)
    events = again.recent()
    assert len(events) == 1
    assert events[0]["title"] == "أنجزت مهمة"


def test_state_events_are_deduplicated_until_state_changes(tmp_path: Path):
    store = ProactiveEventStore(tmp_path)
    first = store.emit("state_tasks_changed", "تغيرت الحالة", "pending=2", dedupe_key="tasks")
    duplicate = store.emit("state_tasks_changed", "تغيرت الحالة", "pending=2", dedupe_key="tasks")
    changed = store.emit("state_tasks_changed", "تغيرت الحالة", "pending=1", dedupe_key="tasks")

    assert not first.get("suppressed")
    assert duplicate.get("suppressed") is True
    assert not changed.get("suppressed")
    assert len(store.recent()) == 2


def test_mark_seen_resets_unread_counter(tmp_path: Path):
    store = ProactiveEventStore(tmp_path)
    event = store.emit("runtime_online", "أمير متصل", "بدأت المراقبة")
    assert store.unread_count() == 1
    store.mark_seen(event["at"])
    assert store.unread_count() == 0
