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
            sensor_id="thermal-runtime-1",
            kind="thermal_radiometric",
            vendor="test",
            model="runtime-fake",
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
            timestamp="2026-09-06T02:00:00Z",
            sequence=1,
            payload={"min_temperature_c": 22.0, "max_temperature_c": 30.0},
        )


def test_runtime_registers_capability_sensor_and_frame(tmp_path):
    registry = CapabilityRegistry(tmp_path)
    runtime = SensesRuntime(registry)
    runtime.register_sensor(FakeAdapter())
    runtime.connect_sensor("thermal-runtime-1")
    frame = runtime.read_sensor("thermal-runtime-1")

    snapshot = runtime.snapshot()
    assert snapshot["capability"]["registered"] is True
    assert snapshot["hardware"]["sensor_count"] == 1
    assert frame.payload["max_temperature_c"] == 30.0
    assert runtime.last_frame("thermal-runtime-1") == frame
    assert snapshot["ready_for_shadow_ui"] is True


def test_runtime_publishes_ui_ready_media(tmp_path):
    runtime = SensesRuntime(CapabilityRegistry(tmp_path))
    asset = MediaAsset(
        asset_id="thermal-image-1",
        kind="image",
        source_sensor_id="thermal-runtime-1",
        uri="media://thermal-image-1",
        mime_type="image/png",
        width=640,
        height=480,
    )
    presentation = MediaPresentationBuilder.image(
        presentation_id="presentation-1",
        title="Thermal frame",
        asset=asset,
    )
    published = runtime.publish_presentation(presentation)

    assert published["primary"]["kind"] == "image"
    assert runtime.snapshot()["presentations"][0]["presentation_id"] == "presentation-1"
