"""
executive_kernel.py
===================
Senses-enabled ExecutiveKernel facade.

The original implementation is preserved in executive_kernel_base.py. This facade
adds the live Extended Senses runtime without rewriting the established executive
pipeline, so existing imports continue to use kernel.executive_kernel.ExecutiveKernel.
"""

from __future__ import annotations

from pathlib import Path

from kernel.executive_kernel_base import ExecutiveKernel as _BaseExecutiveKernel
from kernel.senses_runtime import SensesRuntime


class ExecutiveKernel(_BaseExecutiveKernel):
    """Existing executive kernel plus the live extended-senses runtime."""

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root=workspace_root)
        # SensesRuntime idempotently registers the founder-approved capability and
        # owns SensorHub + analysis + media-presentation state for the live process.
        self.senses: SensesRuntime = SensesRuntime(self.capabilities)

    def boot(self) -> dict:
        report = super().boot()
        try:
            senses_snapshot = self.senses.snapshot()
            self._health["extended_senses_runtime"] = "ok"
            report["components"] = self._health
            report["extended_senses"] = senses_snapshot
        except Exception as exc:
            self._health["extended_senses_runtime"] = f"error: {exc}"
            errors = report.setdefault("errors", [])
            if "extended_senses_runtime" not in errors:
                errors.append("extended_senses_runtime")
            report["status"] = "degraded"
            report["components"] = self._health
        return report

    def before_request(self, query: str) -> dict:
        context = super().before_request(query)
        context["extended_senses"] = self.senses.snapshot()
        return context

    def health(self) -> dict:
        report = super().health()
        try:
            report["extended_senses"] = self.senses.snapshot()
        except Exception as exc:
            report["extended_senses"] = {
                "ready_for_shadow_ui": False,
                "error": str(exc),
            }
        return report
