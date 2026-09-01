from kernel.artifact_capabilities import artifact_policy_snapshot
from kernel.proactive_communication import decide_proactive_communication, outbound_channel_policy, proactive_policy_snapshot


def test_ameer_may_start_conversation_without_founder_message():
    snap = proactive_policy_snapshot()
    assert snap["ameer_may_start_conversation"] is True
    assert snap["founder_does_not_need_to_message_first"] is True


def test_artifact_ready_can_trigger_proactive_delivery():
    decision = decide_proactive_communication(
        "artifact_ready",
        preferred_channels=["whatsapp", "email"],
        delivery_type="file",
    )
    assert decision.may_initiate is True
    assert decision.requires_founder_to_start_conversation is False
    assert decision.preferred_channels == ("whatsapp", "email")


def test_email_and_whatsapp_are_operational_channels_when_connected():
    for channel in ("email", "whatsapp"):
        policy = outbound_channel_policy(channel)
        assert policy["supported"] is True
        assert policy["connector_required"] is True
        assert policy["founder_approval_required_for_ordinary_send"] is False
        assert policy["may_attach_requested_files"] is True


def test_creative_and_engineering_outputs_are_first_class():
    snap = artifact_policy_snapshot()
    caps = snap["capabilities"]
    for name in ("image_generation", "video_generation", "presentations", "documents", "spreadsheets", "code", "web_ui"):
        assert name in caps
    assert caps["video_generation"]["quality_target"] == "high_quality"
    assert snap["ameer_selects_toolchain"] is True
    assert snap["provider_independent"] is True
    assert snap["validation_and_repair_required"] is True
