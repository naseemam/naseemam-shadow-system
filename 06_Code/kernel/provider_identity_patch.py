from __future__ import annotations

from functools import wraps
from typing import Any

from kernel.provider_independent_identity import ProviderIndependentIdentity

_INSTALLED = False


def install_provider_identity_patch() -> None:
    """Attach provider-independent identity to Ameer's existing executive kernel."""
    global _INSTALLED
    if _INSTALLED:
        return

    from kernel.expanded_agent import ExpandedAgentExecutiveKernel

    original_init = ExpandedAgentExecutiveKernel.__init__
    original_capabilities = ExpandedAgentExecutiveKernel.expanded_capabilities

    @wraps(original_init)
    def __init__(self: ExpandedAgentExecutiveKernel, workspace_root, *args: Any, **kwargs: Any) -> None:
        original_init(self, workspace_root, *args, **kwargs)
        self.identity = ProviderIndependentIdentity(workspace_root)

    @wraps(original_capabilities)
    def expanded_capabilities(self: ExpandedAgentExecutiveKernel):
        data = original_capabilities(self)
        data["identity"] = self.identity.profile()
        data["identity_continuity"] = {
            "provider_independent": True,
            "model_independent": True,
            "device_independent": True,
            "channel_independent": True,
            "provider_is_execution_engine_only": True,
        }
        return data

    ExpandedAgentExecutiveKernel.__init__ = __init__
    ExpandedAgentExecutiveKernel.expanded_capabilities = expanded_capabilities
    _INSTALLED = True
