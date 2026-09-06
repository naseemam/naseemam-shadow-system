from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.executive_kernel import ExecutiveKernel


def test_executive_kernel_owns_live_senses_runtime(tmp_path):
    kernel = ExecutiveKernel(workspace_root=tmp_path)

    assert kernel.senses is not None
    assert kernel.senses.capability_registry is kernel.capabilities
    assert kernel.capabilities.get_by_name("extended_senses") is not None

    snapshot = kernel.senses.snapshot()
    assert snapshot["capability"]["registered"] is True
    assert snapshot["hardware"]["sensor_count"] == 0
    assert snapshot["ready_for_shadow_ui"] is True


def test_kernel_health_exposes_extended_senses(tmp_path):
    kernel = ExecutiveKernel(workspace_root=tmp_path)
    health = kernel.health()

    assert "extended_senses" in health
    assert health["extended_senses"]["capability"]["name"] == "extended_senses"
    assert health["extended_senses"]["ready_for_shadow_ui"] is True
