"""
extended_senses.py
==================
Ameer Extended Senses — طبقة الحواس الممتدة لأمير.

هذه الطبقة تتعامل فقط مع قياسات حساسات فعلية. لا تنسب أي إشارة إلى
مصدر خارق أو غير مثبت. تفصل دائمًا بين الرصد، التحليل، والتفسير.

الهدف الأول: دعم إشارات صوتية خارج نطاق السمع البشري، خصوصًا فوق الصوتية،
مع إمكانية تحويل وصفها إلى نطاق مسموع عندما يوفر الحساس/المحوّل البيانات اللازمة.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

HUMAN_HEARING_MIN_HZ = 20.0
HUMAN_HEARING_MAX_HZ = 20_000.0


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


class ExtendedSenses:
    """
    تحليل محايد لقياسات الحساسات.

    هذه الوحدة لا تدّعي أنها تسمع من دون عتاد. تحتاج Sensor Adapter فعليًا
    يرسل القياسات أو التسجيلات إليها.
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


def ensure_extended_senses_capability(capability_registry: Any) -> str:
    """Register the founder-approved capability idempotently.

    Returns the existing or newly created capability_id. Runtime startup code can
    call this helper without duplicating the capability card.
    """
    existing = capability_registry.get_by_name(ExtendedSenses.capability_name)
    if existing is not None:
        return existing["capability_id"]

    return capability_registry.register(
        name=ExtendedSenses.capability_name,
        description=(
            "Ingest and analyze measurements from extended physical sensors, including "
            "ultrasonic acoustic sensors, and present verified observations separately "
            "from unverified source interpretations."
        ),
        scope="sensing",
        approved_by="founder:Naseem",
        status="extended",
        dependencies=["analysis"],
        risk_level="medium",
        version="1.0.0",
        notes=(
            "Founder-approved. Actual sensing requires a compatible hardware sensor/adapter. "
            "Never label anomalous signals as supernatural without independent evidence."
        ),
    )
