from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.capability_registry import CapabilityRegistry
from kernel.media_presentation import MediaAsset, MediaPresentationBuilder
from kernel.sensor_hardware import SensorDescriptor, SensorFrame
from kernel.senses_runtime import SensesRuntime


class FakeAdapter:
    def __init__(self):
        self._descriptor = SensorDescriptor(
            sensor_id="thermal-persist-1",
            kind="thermal_radiometric",
            vendor="test",
            model="persist-fake",
            transport="usb",
            capabilities=("temperature", "frame"),
        )
        self.connected = False

    @property
    def descriptor(self):
        return self._descriptor

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def health(self):
        return {"ok": True}

    def read_frame(self):
        return SensorFrame(
            sensor_id=self._descriptor.sensor_id,
            kind=self._descriptor.kind,
            timestamp="2026-09-06T03:00:00Z",
            sequence=7,
            payload={"min_temperature_c": 23.0, "max_temperature_c": 31.5},
        )


def test_runtime_persists_frames_presentations_and_calibration(tmp_path):
    runtime = SensesRuntime(CapabilityRegistry(tmp_path), workspace_root=tmp_path)
    runtime.register_sensor(FakeAdapter())
    runtime.connect_sensor("thermal-persist-1")
    frame = runtime.read_sensor("thermal-persist-1")

    assert runtime.persisted_last_frame("thermal-persist-1")["sequence"] == 7
    assert frame.payload["max_temperature_c"] == 31.5

    asset = MediaAsset(
        asset_id="persisted-image",
        kind="image",
        source_sensor_id="thermal-persist-1",
        uri="media://persisted-image",
        mime_type="image/png",
    )
    presentation = MediaPresentationBuilder.image(
        presentation_id="persisted-presentation",
        title="Persistent thermal frame",
        asset=asset,
    )
    runtime.publish_presentation(presentation)
    assert runtime.catalog.presentations()[0]["presentation_id"] == "persisted-presentation"

    calibration = runtime.set_calibration("thermal-persist-1", {
        "emissivity": 0.95,
        "source": "device_profile",
    })
    assert calibration["emissivity"] == 0.95
    assert runtime.get_calibration("thermal-persist-1")["source"] == "device_profile"


def test_event_bus_replays_runtime_events(tmp_path):
    runtime = SensesRuntime(CapabilityRegistry(tmp_path), workspace_root=tmp_path)
    runtime.register_sensor(FakeAdapter())
    runtime.connect_sensor("thermal-persist-1")
    runtime.read_sensor("thermal-persist-1")

    events = runtime.events_since(0)
    types = [event["event_type"] for event in events]
    assert types == ["sensor_registered", "sensor_connected", "sensor_frame"]
    cursor = events[1]["event_id"]
    replay = runtime.events_since(cursor)
    assert [event["event_type"] for event in replay] == ["sensor_frame"]


def test_persistence_survives_runtime_restart(tmp_path):
    runtime = SensesRuntime(CapabilityRegistry(tmp_path), workspace_root=tmp_path)
    runtime.register_sensor(FakeAdapter())
    runtime.connect_sensor("thermal-persist-1")
    runtime.read_sensor("thermal-persist-1")
    runtime.set_calibration("thermal-persist-1", {"emissivity": 0.92})

    restarted = SensesRuntime(CapabilityRegistry(tmp_path), workspace_root=tmp_path)
    assert restarted.persisted_last_frame("thermal-persist-1")["sequence"] == 7
    assert restarted.get_calibration("thermal-persist-1")["emissivity"] == 0.92
