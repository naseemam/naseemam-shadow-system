from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.capability_registry import CapabilityRegistry
from kernel.extended_senses import (
    AcousticObservation,
    ExtendedSenses,
    VisionObservation,
    ensure_extended_senses_capability,
)


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


def test_radiometric_thermal_observation_reports_temperature_and_hotspot():
    result = ExtendedSenses().analyze_vision_observation(
        VisionObservation(
            modality="radiometric",
            min_temperature_c=22.4,
            max_temperature_c=41.7,
            mean_temperature_c=29.2,
            hotspot_temperature_c=41.7,
            hotspot_x=0.63,
            hotspot_y=0.28,
            confidence=0.95,
        )
    )
    assert result["thermal_measurement"] is True
    assert result["temperature_summary_c"]["min"] == 22.4
    assert result["temperature_summary_c"]["max"] == 41.7
    assert result["hotspot"]["temperature_c"] == 41.7
    assert result["source_attribution"] == "unknown"
    assert result["source_claim"] is None


def test_nir_is_extended_vision_not_temperature_measurement():
    result = ExtendedSenses().analyze_vision_observation(
        VisionObservation(modality="nir", confidence=0.8)
    )
    assert result["thermal_measurement"] is False
    assert "infrared_note" in result


def test_nir_rejects_temperature_values():
    try:
        ExtendedSenses().analyze_vision_observation(
            VisionObservation(modality="nir", max_temperature_c=35.0)
        )
    except ValueError as exc:
        assert "temperature values require" in str(exc)
    else:
        raise AssertionError("NIR observation with temperature must be rejected")


def test_thermal_rgb_fusion_marks_registered_overlay():
    result = ExtendedSenses().analyze_vision_observation(
        VisionObservation(modality="thermal_rgb_fusion", fused_rgb=True)
    )
    assert result["fusion"]["rgb_registered"] is True


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
