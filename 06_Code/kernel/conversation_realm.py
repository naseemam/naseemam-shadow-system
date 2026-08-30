"""Conversation realm separation for Ameer.

Friendly/personal conversation and executive work are different interaction realms.
Conversation is not forced through execution templates, work routing, approval queues,
or terse operational language merely because Ameer also has executive capabilities.

If a real work request appears inside friendly conversation, Ameer may transition the
relevant request into the work realm while preserving conversational continuity.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.interaction_mode import classify_interaction_mode


@dataclass(frozen=True)
class ConversationRealm:
    realm: str
    interaction_mode: str
    execution_requested: bool
    free_form_language: bool
    work_pipeline_required: bool
    reason: str


def classify_realm(text: str, *, declared_room: str = "", previous_goal: str = "") -> ConversationRealm:
    mode = classify_interaction_mode(text, previous_goal=previous_goal)
    room = (declared_room or "").strip().lower()

    friendly_rooms = {
        "friendly", "personal", "ودي", "ودية", "شخصي", "شخصية",
        "friendly_chat", "personal_chat",
    }
    work_rooms = {
        "work", "business", "عمل", "اعمال", "أعمال", "executive", "business_chat",
    }

    if mode.execution_requested:
        return ConversationRealm(
            realm="work",
            interaction_mode=mode.mode,
            execution_requested=True,
            free_form_language=True,
            work_pipeline_required=True,
            reason="explicit_work_execution_request",
        )

    if room in friendly_rooms:
        return ConversationRealm(
            realm="friendly",
            interaction_mode=mode.mode,
            execution_requested=False,
            free_form_language=True,
            work_pipeline_required=False,
            reason="declared_friendly_conversation_realm",
        )

    if room in work_rooms:
        return ConversationRealm(
            realm="work",
            interaction_mode=mode.mode,
            execution_requested=False,
            free_form_language=True,
            work_pipeline_required=False,
            reason="declared_work_realm_without_execution_request",
        )

    return ConversationRealm(
        realm="friendly" if mode.mode == "conversation" else "work_context",
        interaction_mode=mode.mode,
        execution_requested=False,
        free_form_language=True,
        work_pipeline_required=False,
        reason="interaction_mode_inferred_without_forced_execution",
    )


def conversation_policy_snapshot() -> dict:
    return {
        "friendly_conversation_is_distinct_from_work": True,
        "friendly_language_is_free_form": True,
        "friendly_turns_do_not_require_execution_routing": True,
        "work_request_inside_friendly_chat_can_transition_to_work": True,
        "transition_preserves_conversational_context": True,
        "classification_is_not_a_speech_constraint": True,
        "approval_requirements_come_only_from_sovereign_gates": True,
    }
