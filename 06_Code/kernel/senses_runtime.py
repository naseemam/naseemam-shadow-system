"""
senses_runtime.py
=================
Runtime coordinator for Ameer Extended Senses.

This is the in-process service that joins capability governance, SensorHub,
ExtendedSenses analysis, and MediaPresentationRegistry behind one stable API.
Shadow System HTTP/WebSocket endpoints can expose this service without knowing
vendor SDK details.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from kernel.extended_senses import ExtendedSenses, ensure_extended_senses_capability
from kernel.media_presentation import MediaPresentation, MediaPresentationRegistry
from kernel.sensor_hardware import SensorAdapter, SensorFrame, SensorHub


class SensesRuntime:
    """Live runtime owner for sensors, analysis and UI-ready presentations."""

    def __init__(self, capability_registry: Any) -> None:
        self.capability_registry = capability_registry
        self.capability_id = ensure_extended_senses_capability(capability_registry)
        self.sensor_hub = SensorHub()
        self.analyzer = ExtendedSenses()
        self.presentations = MediaPresentationRegistry()
        self._last_frames: Dict[str, SensorFrame] = {}

    def register_sensor(self, adapter: SensorAdapter) -> dict:
        self.sensor_hub.register(adapter)
        return self.sensor_status(adapter.descriptor.sensor_id)

    def connect_sensor(self, sensor_id: str) -> dict:
        self.sensor_hub.connect(sensor_id)
        return self.sensor_status(sensor_id)

    def disconnect_sensor(self, sensor_id: str) -> dict:
        self.sensor_hub.disconnect(sensor_id)
        return self.sensor_status(sensor_id)

    def read_sensor(self, sensor_id: str) -> SensorFrame:
        frame = self.sensor_hub.read(sensor_id)
        self._last_frames[sensor_id] = frame
        return frame

    def last_frame(self, sensor_id: str) -> Optional[SensorFrame]:
        return self._last_frames.get(sensor_id)

    def publish_presentation(self, presentation: MediaPresentation) -> dict:
        self.presentations.put(presentation)
        return presentation.to_dict()

    def remove_presentation(self, presentation_id: str) -> None:
        self.presentations.remove(presentation_id)

    def sensor_status(self, sensor_id: str) -> dict:
        snapshot = self.sensor_hub.health_snapshot()
        for item in snapshot["sensors"]:
            if item["sensor_id"] == sensor_id:
                return item
        raise KeyError(f"unknown sensor: {sensor_id}")

    def snapshot(self) -> dict:
        hardware = self.sensor_hub.health_snapshot()
        return {
            "capability": {
                "name": "extended_senses",
                "capability_id": self.capability_id,
                "registered": True,
            },
            "hardware": hardware,
            "presentations": self.presentations.list(),
            "last_frame_sensors": sorted(self._last_frames),
            "ready_for_shadow_ui": True,
        }
