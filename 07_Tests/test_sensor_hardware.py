from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.sensor_hardware import SensorDescriptor, SensorFrame, SensorHub


class FakeAdapter:
    def __init__(self, sensor_id="thermal-1", kind="thermal_radiometric"):
        self._descriptor = SensorDescriptor(
            sensor_id=sensor_id,
            kind=kind,
            vendor="test",
            model="fake",
            transport="usb",
            capabilities=("temperature", "frame"),
        )
        self.connected = False
        self.seq = 0

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
        self.seq += 1
        return SensorFrame(
            sensor_id=self._descriptor.sensor_id,
            kind=self._descriptor.kind,
            timestamp="2026-09-06T01:00:00Z",
            sequence=self.seq,
            payload={
                "min_temperature_c": 22.1,
                "max_temperature_c": 31.4,
                "mean_temperature_c": 25.0,
            },
            units={"temperature": "celsius"},
        )


def test_sensor_hub_lifecycle_and_read():
    hub = SensorHub()
    adapter = FakeAdapter()
    hub.register(adapter)
    assert hub.health_snapshot()["sensor_count"] == 1
    assert hub.health_snapshot()["sensors"][0]["connected"] is False

    hub.connect("thermal-1")
    frame = hub.read("thermal-1")
    assert frame.kind == "thermal_radiometric"
    assert frame.payload["max_temperature_c"] == 31.4

    hub.disconnect("thermal-1")
    assert hub.health_snapshot()["sensors"][0]["connected"] is False


def test_duplicate_sensor_id_is_blocked():
    hub = SensorHub()
    hub.register(FakeAdapter())
    try:
        hub.register(FakeAdapter())
        assert False, "expected duplicate registration failure"
    except ValueError as exc:
        assert "already registered" in str(exc)


def test_read_requires_connection():
    hub = SensorHub()
    hub.register(FakeAdapter())
    try:
        hub.read("thermal-1")
        assert False, "expected disconnected sensor failure"
    except RuntimeError as exc:
        assert "not connected" in str(exc)
