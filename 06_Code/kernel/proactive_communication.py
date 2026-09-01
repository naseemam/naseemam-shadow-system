"""Proactive communication contract for Ameer.

Ameer is allowed to initiate communication instead of waiting for the Founder to
speak first. Proactivity is part of the executive role, not an exception.

Examples of proactive triggers:
- a task or workflow needs Founder attention,
- a useful proposal or recommendation is ready,
- an important project change or failure occurred,
- a requested file/artifact is complete,
- a sovereign decision point has been reached with evidence ready,
- a meaningful opportunity, risk, or follow-up has been detected.

Outbound channels are execution resources. When a connected/authorized channel is
available, Ameer may send through it autonomously for ordinary operational
communications. Supported channel kinds include in-app conversation, email, and
WhatsApp-compatible messaging connectors. Channel/provider choice is replaceable.

This module describes Ameer's internal authority model. External service rules,
credentials, and connector availability remain technical prerequisites, not new
Founder approval gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


PROACTIVE_TRIGGERS = (
    "task_attention_needed",
    "proposal_ready",
    "important_change",
    "execution_failure",
    "artifact_ready",
    "sovereign_decision_ready",
    "meaningful_opportunity",
    "meaningful_risk",
    "scheduled_follow_up",
)

OUTBOUND_CHANNELS = (
    "in_app",
    "email",
    "whatsapp",
)

DELIVERY_TYPES = (
    "message",
    "notification",
    "file",
    "report",
    "approval_packet",
    "execution_evidence",
)


@dataclass(frozen=True)
class ProactiveCommunicationDecision:
    may_initiate: bool
    trigger: str
    preferred_channels: tuple[str, ...]
    delivery_type: str
    reason: str
    requires_founder_to_start_conversation: bool = False


def decide_proactive_communication(
    trigger: str,
    *,
    preferred_channels: Optional[Sequence[str]] = None,
    delivery_type: str = "message",
) -> ProactiveCommunicationDecision:
    if trigger not in PROACTIVE_TRIGGERS:
        raise ValueError(f"Unknown proactive trigger: {trigger}")
    if delivery_type not in DELIVERY_TYPES:
        raise ValueError(f"Unknown delivery type: {delivery_type}")

    channels = tuple(ch for ch in (preferred_channels or ("in_app",)) if ch in OUTBOUND_CHANNELS)
    if not channels:
        channels = ("in_app",)

    return ProactiveCommunicationDecision(
        may_initiate=True,
        trigger=trigger,
        preferred_channels=channels,
        delivery_type=delivery_type,
        reason="proactive_executive_communication_is_delegated_by_default",
        requires_founder_to_start_conversation=False,
    )


def outbound_channel_policy(channel: str) -> dict:
    if channel not in OUTBOUND_CHANNELS:
        return {"channel": channel, "supported": False, "reason": "unknown_channel_kind"}
    return {
        "channel": channel,
        "supported": True,
        "operational_authority": "delegated",
        "provider_is_replaceable": True,
        "connector_required": channel != "in_app",
        "founder_approval_required_for_ordinary_send": False,
        "may_attach_requested_files": True,
    }


def proactive_policy_snapshot() -> dict:
    return {
        "ameer_may_start_conversation": True,
        "founder_does_not_need_to_message_first": True,
        "triggers": list(PROACTIVE_TRIGGERS),
        "outbound_channels": list(OUTBOUND_CHANNELS),
        "delivery_types": list(DELIVERY_TYPES),
        "ordinary_outbound_messages_are_operational": True,
        "requested_files_may_be_delivered_outbound": True,
        "channels_are_resources_not_authorities": True,
    }
