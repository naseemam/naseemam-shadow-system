"""
senses_runtime.py
=================
Runtime coordinator for Ameer Extended Senses.

Joins capability governance, SensorHub, analysis, media presentation, persistent
catalog/calibration metadata, and a replayable event feed behind one stable API.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from kernel.extended_senses import ExtendedSenses, ensure_extended_senses_capability
from kernel.media_presentation import MediaPresentation, MediaPresentationRegistry
from kernel.sensor_hardware import SensorAdapter, SensorFrame, SensorHub
from kernel.senses_persistence import CalibrationRegistry, PersistentSensesCatalog, SensesEventBus


class SensesRuntime:
    """Live runtime owner for sensors, analysis, persistence and UI-ready media."""

    def __init__(self, capability_registry: Any, workspace_root: Optional[str | Path] = None) -> None:
        self.capability_registry = capability_registry
        self.capability_id = ensure_extended_senses_capability(capability_registry)
        root = Path(workspace_root or getattr(capability_registry, "_root", ".")).resolve()
        self.sensor_hub = SensorHub()
        self.analyzer = ExtendedSenses()
        self.presentations = MediaPresentationRegistry()
        self.catalog = PersistentSensesCatalog(root)
        self.calibration = CalibrationRegistry(root)
        self.events = SensesEventBus()
        self._last_frames: Dict[str, SensorFrame] = {}

    def register_sensor(self, adapter: SensorAdapter) -> dict:
        self.sensor_hub.register(adapter)
        status = self.sensor_status(adapter.descriptor.sensor_id)
        self.events.publish("sensor_registered", status)
        return status

    def connect_sensor(self, sensor_id: str) -> dict:
        self.sensor_hub.connect(sensor_id)
        status = self.sensor_status(sensor_id)
        self.events.publish("sensor_connected", status)
        return status

    def disconnect_sensor(self, sensor_id: str) -> dict:
        self.sensor_hub.disconnect(sensor_id)
        status = self.sensor_status(sensor_id)
        self.events.publish("sensor_disconnected", status)
        return status

    def read_sensor(self, sensor_id: str) -> SensorFrame:
        frame = self.sensor_hub.read(sensor_id)
        self._last_frames[sensor_id] = frame
        frame_dict = asdict(frame)
        self.catalog.put_frame(sensor_id, frame_dict)
        self.events.publish("sensor_frame", frame_dict)
        return frame

    def last_frame(self, sensor_id: str) -> Optional[SensorFrame]:
        return self._last_frames.get(sensor_id)

    def persisted_last_frame(self, sensor_id: str) -> Optional[dict]:
        return self.catalog.last_frame(sensor_id)

    def publish_presentation(self, presentation: MediaPresentation) -> dict:
        self.presentations.put(presentation)
        payload = presentation.to_dict()
        self.catalog.put_presentation(payload)
        self.events.publish("presentation_published", payload)
        return payload

    def remove_presentation(self, presentation_id: str) -> None:
        self.presentations.remove(presentation_id)
        self.catalog.remove_presentation(presentation_id)
        self.events.publish("presentation_removed", {"presentation_id": presentation_id})

    def set_calibration(self, sensor_id: str, calibration: Mapping[str, Any]) -> dict:
        record = self.calibration.set(sensor_id, calibration)
        self.events.publish("calibration_updated", record)
        return record

    def get_calibration(self, sensor_id: str) -> Optional[dict]:
        return self.calibration.get(sensor_id)

    def sensor_status(self, sensor_id: str) -> dict:
        snapshot = self.sensor_hub.health_snapshot()
        for item in snapshot["sensors"]:
            if item["sensor_id"] == sensor_id:
                return item
        raise KeyError(f"unknown sensor: {sensor_id}")

    def events_since(self, event_id: int = 0) -> list[dict]:
        return self.events.since(event_id)

    def snapshot(self) -> dict:
        hardware = self.sensor_hub.health_snapshot()
        live_presentations = self.presentations.list()
        persisted_presentations = self.catalog.presentations()
        return {
            "capability": {
                "name": "extended_senses",
                "capability_id": self.capability_id,
                "registered": True,
            },
            "hardware": hardware,
            "presentations": live_presentations or persisted_presentations,
            "last_frame_sensors": sorted(set(self._last_frames) | {
                item.get("sensor_id", "") for item in self.calibration.list() if item.get("sensor_id")
            }),
            "persistence": self.catalog.snapshot(),
            "calibration_count": len(self.calibration.list()),
            "event_feed": self.events.snapshot(),
            "ready_for_shadow_ui": True,
            "ready_for_live_transport": True,
        }
