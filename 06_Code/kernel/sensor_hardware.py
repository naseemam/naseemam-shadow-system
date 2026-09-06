"""
sensor_hardware.py
==================
Hardware readiness layer for Ameer Extended Senses.

This module does not pretend hardware exists. It defines the stable contract that
real ultrasonic, thermal, infrared, vibration, and future sensors will plug into.
The goal is "plug-and-adapt": once a supported device is physically connected,
only a device-specific adapter is needed; the rest of Ameer already has a common
sensor API, validation, health reporting, and normalized frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence


SUPPORTED_SENSOR_KINDS = {
    "ultrasonic_audio",
    "infrasound_audio",
    "thermal_lwir",
    "thermal_mwir",
    "thermal_radiometric",
    "nir_camera",
    "swir_camera",
    "rgb_camera",
    "vibration",
}


@dataclass(frozen=True)
class SensorDescriptor:
    sensor_id: str
    kind: str
    vendor: Optional[str] = None
    model: Optional[str] = None
    transport: str = "unknown"  # usb, ethernet, serial, i2c, spi, rtsp, sdk, etc.
    capabilities: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.sensor_id.strip():
            raise ValueError("sensor_id must not be empty")
        if self.kind not in SUPPORTED_SENSOR_KINDS:
            raise ValueError(f"unsupported sensor kind: {self.kind}")


@dataclass(frozen=True)
class SensorFrame:
    sensor_id: str
    kind: str
    timestamp: str
    sequence: int
    payload: Mapping[str, Any]
    units: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.sensor_id.strip():
            raise ValueError("sensor_id must not be empty")
        if self.kind not in SUPPORTED_SENSOR_KINDS:
            raise ValueError(f"unsupported sensor kind: {self.kind}")
        if self.sequence < 0:
            raise ValueError("sequence must be >= 0")
        if not self.timestamp.strip():
            raise ValueError("timestamp must not be empty")


class SensorAdapter(Protocol):
    """Contract every physical device adapter must satisfy."""

    @property
    def descriptor(self) -> SensorDescriptor: ...

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def is_connected(self) -> bool: ...

    def health(self) -> Mapping[str, Any]: ...

    def read_frame(self) -> SensorFrame: ...


class SensorHub:
    """In-process registry and lifecycle manager for physical sensor adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, SensorAdapter] = {}

    def register(self, adapter: SensorAdapter) -> None:
        descriptor = adapter.descriptor
        descriptor.validate()
        if descriptor.sensor_id in self._adapters:
            raise ValueError(f"sensor already registered: {descriptor.sensor_id}")
        self._adapters[descriptor.sensor_id] = adapter

    def unregister(self, sensor_id: str) -> None:
        adapter = self._adapters.get(sensor_id)
        if adapter is None:
            return
        if adapter.is_connected():
            adapter.disconnect()
        del self._adapters[sensor_id]

    def connect(self, sensor_id: str) -> None:
        self._require(sensor_id).connect()

    def disconnect(self, sensor_id: str) -> None:
        self._require(sensor_id).disconnect()

    def read(self, sensor_id: str) -> SensorFrame:
        adapter = self._require(sensor_id)
        if not adapter.is_connected():
            raise RuntimeError(f"sensor is not connected: {sensor_id}")
        frame = adapter.read_frame()
        frame.validate()
        if frame.sensor_id != sensor_id:
            raise ValueError("adapter returned frame for a different sensor_id")
        return frame

    def descriptors(self) -> List[SensorDescriptor]:
        return [adapter.descriptor for adapter in self._adapters.values()]

    def health_snapshot(self) -> Dict[str, Any]:
        sensors: List[Dict[str, Any]] = []
        for adapter in self._adapters.values():
            descriptor = adapter.descriptor
            try:
                health = dict(adapter.health())
                error = None
            except Exception as exc:  # health reporting must not break whole hub
                health = {}
                error = str(exc)
            sensors.append(
                {
                    "sensor_id": descriptor.sensor_id,
                    "kind": descriptor.kind,
                    "transport": descriptor.transport,
                    "connected": bool(adapter.is_connected()),
                    "health": health,
                    "health_error": error,
                }
            )
        return {"sensor_count": len(sensors), "sensors": sensors}

    def _require(self, sensor_id: str) -> SensorAdapter:
        try:
            return self._adapters[sensor_id]
        except KeyError as exc:
            raise KeyError(f"unknown sensor: {sensor_id}") from exc


# Adapter-specific normalization expectations. Real device integrations can use
# these keys so ExtendedSenses receives stable data regardless of vendor SDK.
NORMALIZED_PAYLOAD_SCHEMAS: Dict[str, Dict[str, str]] = {
    "ultrasonic_audio": {
        "dominant_frequency_hz": "float",
        "level_db": "float?",
        "duration_ms": "float?",
        "sample_rate_hz": "float?",
    },
    "infrasound_audio": {
        "dominant_frequency_hz": "float",
        "level_db": "float?",
        "duration_ms": "float?",
        "sample_rate_hz": "float?",
    },
    "thermal_radiometric": {
        "min_temperature_c": "float",
        "max_temperature_c": "float",
        "mean_temperature_c": "float?",
        "hotspots": "list[object]?",
        "frame_width": "int?",
        "frame_height": "int?",
    },
    "thermal_lwir": {"image_ref": "str?", "relative_intensity": "array?"},
    "thermal_mwir": {"image_ref": "str?", "relative_intensity": "array?"},
    "nir_camera": {"image_ref": "str?", "relative_intensity": "array?"},
    "swir_camera": {"image_ref": "str?", "relative_intensity": "array?"},
    "rgb_camera": {"image_ref": "str?"},
    "vibration": {"frequency_hz": "float?", "amplitude": "float?"},
}
