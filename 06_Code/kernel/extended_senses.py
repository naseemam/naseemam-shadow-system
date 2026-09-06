"""
extended_senses.py
==================
Ameer Extended Senses — طبقة الحواس الممتدة لأمير.

هذه الطبقة تتعامل فقط مع قياسات حساسات فعلية. لا تنسب أي إشارة إلى
مصدر خارق أو غير مثبت. تفصل دائمًا بين الرصد، التحليل، والتفسير.

تدعم الطبقة حاليًا:
- الإشارات الصوتية تحت/داخل/فوق نطاق السمع البشري.
- الرؤية الحرارية وتحت الحمراء: LWIR / MWIR / NIR / SWIR.
- القياسات الحرارية radiometric عند توفر درجات حرارة فعلية من الحساس.
- دمج Thermal + RGB على مستوى metadata، مع إبقاء مصدر كل قياس واضحًا.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

HUMAN_HEARING_MIN_HZ = 20.0
HUMAN_HEARING_MAX_HZ = 20_000.0

THERMAL_MODALITIES = {"lwir", "mwir", "radiometric"}
REFLECTED_IR_MODALITIES = {"nir", "swir"}
SUPPORTED_VISION_MODALITIES = THERMAL_MODALITIES | REFLECTED_IR_MODALITIES | {
    "rgb",
    "thermal_rgb_fusion",
}


@dataclass(frozen=True)
class AcousticObservation:
    """قياس موثق قادم من حساس صوتي أو محلل طيف."""

    dominant_frequency_hz: float
    level_db: Optional[float] = None
    duration_ms: Optional[float] = None
    sensor_id: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: Optional[float] = None

    def validate(self) -> None:
        if self.dominant_frequency_hz < 0:
            raise ValueError("dominant_frequency_hz must be >= 0")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be >= 0")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class VisionObservation:
    """ملخص موثق لقطة/إطار من حساس رؤية ممتدة."""

    modality: str
    sensor_id: Optional[str] = None
    timestamp: Optional[str] = None
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    mean_temperature_c: Optional[float] = None
    hotspot_temperature_c: Optional[float] = None
    hotspot_x: Optional[float] = None
    hotspot_y: Optional[float] = None
    confidence: Optional[float] = None
    fused_rgb: bool = False

    def validate(self) -> None:
        modality = self.modality.strip().lower()
        if modality not in SUPPORTED_VISION_MODALITIES:
            raise ValueError(f"unsupported vision modality: {self.modality}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        for name, value in (("hotspot_x", self.hotspot_x), ("hotspot_y", self.hotspot_y)):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be normalized between 0 and 1")
        temps = [
            self.min_temperature_c,
            self.max_temperature_c,
            self.mean_temperature_c,
            self.hotspot_temperature_c,
        ]
        if modality not in THERMAL_MODALITIES and any(v is not None for v in temps):
            raise ValueError(
                "temperature values require a thermal/radiometric modality; "
                "NIR/SWIR are reflected-infrared modalities, not direct temperature measurements"
            )
        if (
            self.min_temperature_c is not None
            and self.max_temperature_c is not None
            and self.min_temperature_c > self.max_temperature_c
        ):
            raise ValueError("min_temperature_c must be <= max_temperature_c")


class ExtendedSenses:
    """
    تحليل محايد لقياسات الحساسات.

    هذه الوحدة لا تدّعي أنها تسمع أو ترى أطيافًا غير بشرية من دون عتاد.
    تحتاج Sensor Adapter فعليًا يرسل القياسات أو التسجيلات/الإطارات إليها.
    """

    capability_name = "extended_senses"

    @staticmethod
    def acoustic_band(frequency_hz: float) -> str:
        if frequency_hz < 0:
            raise ValueError("frequency_hz must be >= 0")
        if frequency_hz < HUMAN_HEARING_MIN_HZ:
            return "infrasound"
        if frequency_hz <= HUMAN_HEARING_MAX_HZ:
            return "audible"
        return "ultrasound"

    @staticmethod
    def audible_shift(
        frequency_hz: float,
        *,
        target_min_hz: float = 500.0,
        target_max_hz: float = 5_000.0,
        source_min_hz: float = 20_000.0,
        source_max_hz: float = 100_000.0,
    ) -> float:
        """Map a measured ultrasonic frequency to a representative audible tone.

        This is a visualization/listening aid, not a claim that the mapped tone is
        the original physical frequency.
        """
        if source_max_hz <= source_min_hz:
            raise ValueError("source_max_hz must be greater than source_min_hz")
        if target_max_hz <= target_min_hz:
            raise ValueError("target_max_hz must be greater than target_min_hz")
        clipped = min(max(frequency_hz, source_min_hz), source_max_hz)
        ratio = (clipped - source_min_hz) / (source_max_hz - source_min_hz)
        return target_min_hz + ratio * (target_max_hz - target_min_hz)

    def analyze_acoustic_observation(self, observation: AcousticObservation) -> Dict[str, Any]:
        observation.validate()
        band = self.acoustic_band(observation.dominant_frequency_hz)
        result: Dict[str, Any] = {
            "observation": asdict(observation),
            "band": band,
            "measured": True,
            "source_attribution": "unknown",
            "source_claim": None,
            "interpretation_policy": (
                "Report the measured signal first. Do not attribute it to a person, animal, "
                "device, spirit, or other source without independent evidence."
            ),
        }
        if band == "ultrasound":
            result["audible_representation_hz"] = round(
                self.audible_shift(observation.dominant_frequency_hz), 2
            )
            result["audible_representation_note"] = (
                "Frequency-shifted representation for human listening; not the original frequency."
            )
        return result

    def analyze_vision_observation(self, observation: VisionObservation) -> Dict[str, Any]:
        observation.validate()
        modality = observation.modality.strip().lower()
        is_thermal = modality in THERMAL_MODALITIES
        result: Dict[str, Any] = {
            "observation": asdict(observation),
            "modality": modality,
            "measured": True,
            "thermal_measurement": is_thermal,
            "source_attribution": "unknown",
            "source_claim": None,
            "interpretation_policy": (
                "Report measured pixels/temperatures first. Do not infer identity, intent, "
                "medical condition, supernatural origin, or hidden cause from an anomalous "
                "thermal/infrared pattern without independent evidence."
            ),
        }
        if is_thermal:
            temps = [
                value
                for value in (
                    observation.min_temperature_c,
                    observation.max_temperature_c,
                    observation.mean_temperature_c,
                    observation.hotspot_temperature_c,
                )
                if value is not None
            ]
            if temps:
                result["temperature_summary_c"] = {
                    "min": min(temps),
                    "max": max(temps),
                    "span": round(max(temps) - min(temps), 3),
                }
            if observation.hotspot_temperature_c is not None:
                result["hotspot"] = {
                    "temperature_c": observation.hotspot_temperature_c,
                    "x": observation.hotspot_x,
                    "y": observation.hotspot_y,
                }
        else:
            result["infrared_note"] = (
                "NIR/SWIR primarily measure reflected infrared energy. Treat them as extended "
                "vision, not as direct body/object temperature measurements."
            )
        if observation.fused_rgb or modality == "thermal_rgb_fusion":
            result["fusion"] = {
                "rgb_registered": True,
                "note": "Keep RGB and extended-spectrum provenance separate when presenting overlays.",
            }
        return result


def ensure_extended_senses_capability(capability_registry: Any) -> str:
    """Register the founder-approved capability idempotently."""
    existing = capability_registry.get_by_name(ExtendedSenses.capability_name)
    if existing is not None:
        return existing["capability_id"]

    return capability_registry.register(
        name=ExtendedSenses.capability_name,
        description=(
            "Ingest and analyze measurements from extended physical sensors, including "
            "ultrasonic/infrasonic audio and thermal/infrared vision (LWIR, MWIR, NIR, SWIR, "
            "radiometric and RGB fusion), while separating verified observations from "
            "unverified source interpretations."
        ),
        scope="sensing",
        approved_by="founder:Naseem",
        status="extended",
        dependencies=["analysis"],
        risk_level="medium",
        version="1.1.0",
        notes=(
            "Founder-approved. Actual sensing requires compatible hardware sensor adapters. "
            "Never label anomalous acoustic, thermal, or infrared signals as supernatural or "
            "as proof of identity/intent without independent evidence."
        ),
    )
