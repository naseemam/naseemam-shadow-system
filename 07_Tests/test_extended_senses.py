from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.capability_registry import CapabilityRegistry
from kernel.extended_senses import AcousticObservation, ExtendedSenses, ensure_extended_senses_capability


def test_acoustic_band_classification():
    senses = ExtendedSenses()
    assert senses.acoustic_band(10) == "infrasound"
    assert senses.acoustic_band(1_000) == "audible"
    assert senses.acoustic_band(40_000) == "ultrasound"


def test_ultrasound_observation_is_reported_without_source_claim():
    result = ExtendedSenses().analyze_acoustic_observation(
        AcousticObservation(dominant_frequency_hz=40_000, confidence=0.9)
    )
    assert result["band"] == "ultrasound"
    assert result["measured"] is True
    assert result["source_attribution"] == "unknown"
    assert result["source_claim"] is None
    assert 500 <= result["audible_representation_hz"] <= 5_000


def test_capability_registration_is_idempotent(tmp_path):
    registry = CapabilityRegistry(tmp_path)
    first = ensure_extended_senses_capability(registry)
    second = ensure_extended_senses_capability(registry)
    assert first == second
    card = registry.get_by_name("extended_senses")
    assert card is not None
    assert card["status"] == "extended"
    assert card["approved_by"] == "founder:Naseem"
    assert card["dependencies"] == ["analysis"]
