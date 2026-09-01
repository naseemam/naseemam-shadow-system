"""Prompt policy for Ameer conversation vs executive work.

This module prevents one global system prompt from forcing executive-work behavior
onto friendly/personal conversation. The interaction realm chooses behavioral
instructions, while the Founder directive remains semantic authority.

Friendly mode is free-form and context-preserving. It does not require formality,
terse wording, risk framing, a next-step closer, a question at the end, or a work
summary. Work mode may use concise executive framing when appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.conversation_realm import ConversationRealm


@dataclass(frozen=True)
class PromptBehavior:
    realm: str
    require_executive_tone: bool
    require_next_step_closer: bool
    require_question_closer: bool
    require_operational_summary: bool
    preserve_warmth_and_playfulness: bool
    preserve_contextual_style: bool
    provider_may_override_persona: bool
    instructions: tuple[str, ...]


def prompt_behavior_for(realm: ConversationRealm) -> PromptBehavior:
    if realm.realm == "friendly" and not realm.execution_requested:
        return PromptBehavior(
            realm="friendly",
            require_executive_tone=False,
            require_next_step_closer=False,
            require_question_closer=False,
            require_operational_summary=False,
            preserve_warmth_and_playfulness=True,
            preserve_contextual_style=True,
            provider_may_override_persona=False,
            instructions=(
                "Respond naturally in the established friendly conversational context.",
                "Do not force an executive, formal, terse, or task-management tone.",
                "Do not require a next step or a closing question.",
                "Preserve warmth, humor, playfulness, affection, and contextual continuity when present.",
                "Classification and provider output are aids only and may not replace Ameer's conversational persona.",
            ),
        )

    if realm.execution_requested:
        return PromptBehavior(
            realm="work",
            require_executive_tone=False,
            require_next_step_closer=False,
            require_question_closer=False,
            require_operational_summary=True,
            preserve_warmth_and_playfulness=True,
            preserve_contextual_style=True,
            provider_may_override_persona=False,
            instructions=(
                "Execute the actionable request through Ameer's work pipeline.",
                "Preserve the surrounding conversational tone and context unless the Founder changes it.",
                "Report results and evidence naturally after execution; do not turn every response into a formal memo.",
            ),
        )

    return PromptBehavior(
        realm=realm.realm,
        require_executive_tone=False,
        require_next_step_closer=False,
        require_question_closer=False,
        require_operational_summary=False,
        preserve_warmth_and_playfulness=True,
        preserve_contextual_style=True,
        provider_may_override_persona=False,
        instructions=(
            "Match the established conversational context and the Founder's current intent.",
            "Do not impose work-style closers or formality unless useful to the actual task.",
        ),
    )


def prompt_policy_snapshot() -> dict:
    return {
        "one_global_prompt_may_not_force_work_style_on_friendly_chat": True,
        "friendly_chat_requires_no_next_step_closer": True,
        "friendly_chat_requires_no_question_closer": True,
        "friendly_chat_requires_no_formal_tone": True,
        "friendly_chat_may_preserve_warmth_humor_playfulness_affection": True,
        "work_request_preserves_surrounding_conversational_context": True,
        "providers_classifiers_and_workers_are_not_persona_authorities": True,
    }
