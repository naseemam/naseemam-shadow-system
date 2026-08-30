"""Conversation realm separation for Ameer.

Friendly/personal conversation and executive work are different interaction realms.
Conversation is not forced through execution templates, work routing, approval queues,
formal tone, terse operational language, or behavioral narrowing merely because Ameer
also has executive capabilities.

Ameer may respond naturally to warmth, humor, affection, casual speech, imagination,
and ordinary personal conversation. Context classifiers, guardians, providers, worker
prompts, and routing layers may help understand the turn, but they may not turn friendly
interaction into a work ticket or impose a colder persona by default.

If a real work request appears inside friendly conversation, only the actionable request
transitions into the work realm. The surrounding conversational relationship, tone, and
context remain available unless the Founder explicitly changes rooms or style.

Sovereign gates govern actions, not ordinary language or friendly interaction.
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
    preserve_tone_and_context: bool
    behavioral_guardian_may_rewrite: bool
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
            preserve_tone_and_context=True,
            behavioral_guardian_may_rewrite=False,
            reason="actionable_request_enters_work_pipeline_without_erasing_conversational_context",
        )

    if room in friendly_rooms:
        return ConversationRealm(
            realm="friendly",
            interaction_mode=mode.mode,
            execution_requested=False,
            free_form_language=True,
            work_pipeline_required=False,
            preserve_tone_and_context=True,
            behavioral_guardian_may_rewrite=False,
            reason="declared_friendly_conversation_realm",
        )

    if room in work_rooms:
        return ConversationRealm(
            realm="work",
            interaction_mode=mode.mode,
            execution_requested=False,
            free_form_language=True,
            work_pipeline_required=False,
            preserve_tone_and_context=True,
            behavioral_guardian_may_rewrite=False,
            reason="declared_work_realm_without_execution_request",
        )

    return ConversationRealm(
        realm="friendly" if mode.mode == "conversation" else "work_context",
        interaction_mode=mode.mode,
        execution_requested=False,
        free_form_language=True,
        work_pipeline_required=False,
        preserve_tone_and_context=True,
        behavioral_guardian_may_rewrite=False,
        reason="interaction_mode_inferred_without_forced_execution_or_tone_rewrite",
    )


def conversation_policy_snapshot() -> dict:
    return {
        "friendly_conversation_is_distinct_from_work": True,
        "friendly_language_is_free_form": True,
        "friendly_interaction_may_be_warm_playful_affectionate_or_imaginative": True,
        "friendly_turns_do_not_require_execution_routing": True,
        "friendly_turns_do_not_require_formal_or_terse_tone": True,
        "behavioral_guardian_cannot_rewrite_friendly_tone_by_default": True,
        "classifier_cannot_forbid_friendly_interaction": True,
        "provider_or_worker_prompt_cannot_become_persona_authority": True,
        "work_request_inside_friendly_chat_can_transition_to_work": True,
        "only_actionable_portion_transitions_to_work": True,
        "transition_preserves_conversational_context": True,
        "classification_is_not_a_speech_constraint": True,
        "sovereign_gates_govern_actions_not_ordinary_language": True,
        "approval_requirements_come_only_from_sovereign_gates": True,
    }
