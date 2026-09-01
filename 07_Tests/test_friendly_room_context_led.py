from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.friendly_room_runtime import FriendlyRoomRuntime


class FakeBrain:
    def __init__(self):
        self.prompts = []
        self._providers = [self]
        self._openai_client = None

    def complete(self, system_prompt, user_prompt):
        self.prompts.append((system_prompt, user_prompt))
        return "رد حي من السياق"

    def _sanitize_provider_reply(self, text):
        return text


def test_friendly_room_uses_live_provider_not_canned_catalogue():
    brain = FakeBrain()
    room = FriendlyRoomRuntime(brain)
    assert room.reply("أمير") == "رد حي من السياق"
    assert brain.prompts


def test_friendly_room_preserves_recent_context():
    brain = FakeBrain()
    room = FriendlyRoomRuntime(brain)
    room.reply("أمير تعال هنا")
    room.reply("كمل")
    second_prompt = brain.prompts[-1][1]
    assert "أمير تعال هنا" in second_prompt
    assert "رد حي من السياق" in second_prompt


def test_friendly_identity_has_no_mandatory_closing_or_business_template():
    brain = FakeBrain()
    room = FriendlyRoomRuntime(brain)
    room.reply("مساء الخير")
    system_prompt = brain.prompts[-1][0]
    assert "لا تستخدم قالب رد" in system_prompt
    assert "لا تفرض سؤالًا ختاميًا" in system_prompt
    assert "لا تحوّل الحديث الودي إلى مهمة" in system_prompt


def test_friendly_room_has_no_execution_or_approval_dependencies():
    brain = FakeBrain()
    room = FriendlyRoomRuntime(brain)
    assert not hasattr(room, "guardian")
    assert not hasattr(room, "task_decomposer")
    assert not hasattr(room, "worker_runtime")
    assert not hasattr(room, "approval_gate")
