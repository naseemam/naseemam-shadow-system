"""
sensor_hardware.py
==================
Hardware readiness layer for Ameer Extended Senses.

This module defines the stable contract that real ultrasonic, thermal, infrared,
vibration, and future sensors plug into. It also prepares Ameer to discover a
connected device, identify its vendor/model, install the required driver/SDK via
a constrained installer, create the correct adapter, connect it, validate health,
and operate it through a common API.
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
                    "vendor": descriptor.vendor,
                    "model": descriptor.model,
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


@dataclass(frozen=True)
class DetectedDevice:
    """Raw hardware identity discovered from the host before an adapter exists."""

    hardware_id: str
    transport: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    serial_number: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.hardware_id.strip():
            raise ValueError("hardware_id must not be empty")
        if not self.transport.strip():
            raise ValueError("transport must not be empty")


@dataclass(frozen=True)
class InstallationRecipe:
    """Vendor/device-specific installation plan executed by an installer backend."""

    recipe_id: str
    vendor: str
    model: str
    sensor_kind: str
    driver_name: Optional[str] = None
    sdk_name: Optional[str] = None
    min_sdk_version: Optional[str] = None
    notes: str = ""

    def validate(self) -> None:
        if not self.recipe_id.strip():
            raise ValueError("recipe_id must not be empty")
        if self.sensor_kind not in SUPPORTED_SENSOR_KINDS:
            raise ValueError(f"unsupported sensor kind: {self.sensor_kind}")


class HardwareProbe(Protocol):
    """OS/platform backend that enumerates currently connected hardware."""

    def discover(self) -> Sequence[DetectedDevice]: ...


class DriverInstaller(Protocol):
    """Constrained installer backend; implementation may use OS/package/vendor tools."""

    def is_installed(self, recipe: InstallationRecipe, device: DetectedDevice) -> bool: ...

    def install(self, recipe: InstallationRecipe, device: DetectedDevice) -> Mapping[str, Any]: ...


class SensorAdapterFactory(Protocol):
    """Factory for one vendor/model family."""

    def matches(self, device: DetectedDevice) -> bool: ...

    def identify(self, device: DetectedDevice) -> Mapping[str, Any]: ...

    def installation_recipe(self, device: DetectedDevice) -> Optional[InstallationRecipe]: ...

    def create_adapter(self, device: DetectedDevice) -> SensorAdapter: ...


class HardwareProvisioner:
    """Discover → identify → install → adapt → connect → validate → operate.

    Ameer can call this service when hardware is physically attached. Device/model
    knowledge lives in adapter factories, so adding support for a new camera or
    microphone does not require changing the SensorHub or ExtendedSenses core.
    """

    def __init__(
        self,
        hub: SensorHub,
        probe: HardwareProbe,
        factories: Sequence[SensorAdapterFactory],
        installer: Optional[DriverInstaller] = None,
    ) -> None:
        self._hub = hub
        self._probe = probe
        self._factories = list(factories)
        self._installer = installer

    def discover(self) -> List[DetectedDevice]:
        devices = list(self._probe.discover())
        for device in devices:
            device.validate()
        return devices

    def inspect(self, device: DetectedDevice) -> Dict[str, Any]:
        factory = self._match_factory(device)
        if factory is None:
            return {
                "hardware_id": device.hardware_id,
                "supported": False,
                "vendor": device.vendor,
                "model": device.model,
                "transport": device.transport,
                "reason": "no_matching_adapter_factory",
            }
        identified = dict(factory.identify(device))
        recipe = factory.installation_recipe(device)
        return {
            "hardware_id": device.hardware_id,
            "supported": True,
            "vendor": identified.get("vendor", device.vendor),
            "model": identified.get("model", device.model),
            "sensor_kind": identified.get("sensor_kind"),
            "transport": device.transport,
            "installation_recipe": recipe.recipe_id if recipe else None,
            "identity": identified,
        }

    def provision(self, device: DetectedDevice, *, auto_connect: bool = True) -> Dict[str, Any]:
        device.validate()
        factory = self._match_factory(device)
        if factory is None:
            raise LookupError(f"unsupported hardware model: {device.hardware_id}")

        identity = dict(factory.identify(device))
        recipe = factory.installation_recipe(device)
        install_result: Dict[str, Any] = {"required": recipe is not None, "performed": False}
        if recipe is not None:
            recipe.validate()
            if self._installer is None:
                raise RuntimeError(
                    f"driver/SDK required for {device.hardware_id} but no installer backend is configured"
                )
            already_installed = self._installer.is_installed(recipe, device)
            install_result["already_installed"] = bool(already_installed)
            if not already_installed:
                install_result.update(dict(self._installer.install(recipe, device)))
                install_result["performed"] = True

        adapter = factory.create_adapter(device)
        descriptor = adapter.descriptor
        descriptor.validate()
        self._hub.register(adapter)

        if auto_connect:
            self._hub.connect(descriptor.sensor_id)

        health = dict(adapter.health())
        connected = bool(adapter.is_connected())
        if auto_connect and not connected:
            raise RuntimeError(f"adapter failed to connect: {descriptor.sensor_id}")

        return {
            "hardware_id": device.hardware_id,
            "sensor_id": descriptor.sensor_id,
            "vendor": descriptor.vendor or identity.get("vendor"),
            "model": descriptor.model or identity.get("model"),
            "kind": descriptor.kind,
            "transport": descriptor.transport,
            "installation": install_result,
            "connected": connected,
            "health": health,
            "ready": connected and health.get("ok", True) is not False,
        }

    def provision_all(self, *, auto_connect: bool = True) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for device in self.discover():
            info = self.inspect(device)
            if not info["supported"]:
                results.append(info)
                continue
            results.append(self.provision(device, auto_connect=auto_connect))
        return results

    def operate_once(self, sensor_id: str) -> SensorFrame:
        """Use an installed/connected sensor for one normalized acquisition cycle."""
        return self._hub.read(sensor_id)

    def stop(self, sensor_id: str) -> None:
        self._hub.disconnect(sensor_id)

    def _match_factory(self, device: DetectedDevice) -> Optional[SensorAdapterFactory]:
        for factory in self._factories:
            if factory.matches(device):
                return factory
        return None


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
