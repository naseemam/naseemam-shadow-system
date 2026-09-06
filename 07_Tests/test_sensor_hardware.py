from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.sensor_hardware import (
    DetectedDevice,
    HardwareProvisioner,
    InstallationRecipe,
    SensorDescriptor,
    SensorFrame,
    SensorHub,
)


class FakeAdapter:
    def __init__(self, sensor_id="thermal-1", kind="thermal_radiometric", vendor="test", model="fake"):
        self._descriptor = SensorDescriptor(
            sensor_id=sensor_id,
            kind=kind,
            vendor=vendor,
            model=model,
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


class FakeProbe:
    def discover(self):
        return [
            DetectedDevice(
                hardware_id="usb:1234:5678:ABC",
                transport="usb",
                vendor_id="1234",
                product_id="5678",
                serial_number="ABC",
            )
        ]


class FakeInstaller:
    def __init__(self):
        self.installed = False
        self.install_calls = 0

    def is_installed(self, recipe, device):
        return self.installed

    def install(self, recipe, device):
        self.install_calls += 1
        self.installed = True
        return {"driver": recipe.driver_name, "sdk": recipe.sdk_name, "ok": True}


class FakeFactory:
    def matches(self, device):
        return device.vendor_id == "1234" and device.product_id == "5678"

    def identify(self, device):
        return {"vendor": "Acme Thermal", "model": "HeatSight X1", "sensor_kind": "thermal_radiometric"}

    def installation_recipe(self, device):
        return InstallationRecipe(
            recipe_id="acme-heatsight-x1",
            vendor="Acme Thermal",
            model="HeatSight X1",
            sensor_kind="thermal_radiometric",
            driver_name="acme-thermal-driver",
            sdk_name="acme-thermal-sdk",
        )

    def create_adapter(self, device):
        return FakeAdapter(vendor="Acme Thermal", model="HeatSight X1")


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


def test_provisioner_discovers_identifies_installs_connects_and_operates():
    hub = SensorHub()
    installer = FakeInstaller()
    provisioner = HardwareProvisioner(hub, FakeProbe(), [FakeFactory()], installer)

    devices = provisioner.discover()
    assert len(devices) == 1

    info = provisioner.inspect(devices[0])
    assert info["supported"] is True
    assert info["vendor"] == "Acme Thermal"
    assert info["model"] == "HeatSight X1"
    assert info["sensor_kind"] == "thermal_radiometric"

    result = provisioner.provision(devices[0])
    assert result["ready"] is True
    assert result["connected"] is True
    assert result["model"] == "HeatSight X1"
    assert installer.install_calls == 1

    frame = provisioner.operate_once("thermal-1")
    assert frame.payload["max_temperature_c"] == 31.4

    provisioner.stop("thermal-1")
    assert hub.health_snapshot()["sensors"][0]["connected"] is False


def test_provisioner_skips_reinstall_when_driver_is_already_present():
    hub = SensorHub()
    installer = FakeInstaller()
    installer.installed = True
    provisioner = HardwareProvisioner(hub, FakeProbe(), [FakeFactory()], installer)
    result = provisioner.provision(provisioner.discover()[0])
    assert result["installation"]["already_installed"] is True
    assert result["installation"]["performed"] is False
    assert installer.install_calls == 0
