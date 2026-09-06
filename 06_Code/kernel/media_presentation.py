"""
media_presentation.py
=====================
Presentation layer for Ameer Extended Senses media.

Normalizes image, video, audio, live-stream, waveform, spectrogram, and thermal/RGB
presentation descriptors so Shadow System can render sensor evidence without being
coupled to a specific vendor SDK or storage backend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence


SUPPORTED_MEDIA_KINDS = {
    "image",
    "video",
    "audio",
    "live_stream",
    "waveform",
    "spectrogram",
    "thermal_overlay",
}


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    kind: str
    source_sensor_id: str
    uri: str
    mime_type: Optional[str] = None
    timestamp: Optional[str] = None
    duration_ms: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sample_rate_hz: Optional[float] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id must not be empty")
        if self.kind not in SUPPORTED_MEDIA_KINDS:
            raise ValueError(f"unsupported media kind: {self.kind}")
        if not self.source_sensor_id.strip():
            raise ValueError("source_sensor_id must not be empty")
        if not self.uri.strip():
            raise ValueError("uri must not be empty")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be >= 0")
        if self.width is not None and self.width <= 0:
            raise ValueError("width must be > 0")
        if self.height is not None and self.height <= 0:
            raise ValueError("height must be > 0")
        if self.sample_rate_hz is not None and self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be > 0")


@dataclass(frozen=True)
class MediaPresentation:
    presentation_id: str
    title: str
    primary: MediaAsset
    related: Sequence[MediaAsset] = field(default_factory=tuple)
    annotations: Mapping[str, Any] = field(default_factory=dict)
    controls: Sequence[str] = field(default_factory=tuple)
    live: bool = False

    def validate(self) -> None:
        if not self.presentation_id.strip():
            raise ValueError("presentation_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        self.primary.validate()
        for asset in self.related:
            asset.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "presentation_id": self.presentation_id,
            "title": self.title,
            "primary": asdict(self.primary),
            "related": [asdict(asset) for asset in self.related],
            "annotations": dict(self.annotations),
            "controls": list(self.controls),
            "live": self.live,
        }


class MediaPresentationBuilder:
    """Build UI-ready presentation cards for sensor-originated media."""

    IMAGE_CONTROLS = ("zoom", "pan", "freeze_frame", "save_snapshot", "compare")
    VIDEO_CONTROLS = ("play", "pause", "seek", "speed", "freeze_frame", "save_snapshot")
    AUDIO_CONTROLS = ("play", "pause", "seek", "volume", "speed")
    LIVE_CONTROLS = ("play", "pause", "freeze_frame", "save_snapshot")

    @classmethod
    def image(cls, *, presentation_id: str, title: str, asset: MediaAsset,
              related: Sequence[MediaAsset] = (), annotations: Mapping[str, Any] = {}) -> MediaPresentation:
        if asset.kind not in {"image", "thermal_overlay"}:
            raise ValueError("image presentation requires image or thermal_overlay asset")
        return MediaPresentation(
            presentation_id=presentation_id,
            title=title,
            primary=asset,
            related=related,
            annotations=annotations,
            controls=cls.IMAGE_CONTROLS,
            live=False,
        )

    @classmethod
    def video(cls, *, presentation_id: str, title: str, asset: MediaAsset,
              related: Sequence[MediaAsset] = (), annotations: Mapping[str, Any] = {}) -> MediaPresentation:
        if asset.kind != "video":
            raise ValueError("video presentation requires video asset")
        return MediaPresentation(
            presentation_id=presentation_id,
            title=title,
            primary=asset,
            related=related,
            annotations=annotations,
            controls=cls.VIDEO_CONTROLS,
            live=False,
        )

    @classmethod
    def audio(cls, *, presentation_id: str, title: str, asset: MediaAsset,
              related: Sequence[MediaAsset] = (), annotations: Mapping[str, Any] = {}) -> MediaPresentation:
        if asset.kind != "audio":
            raise ValueError("audio presentation requires audio asset")
        return MediaPresentation(
            presentation_id=presentation_id,
            title=title,
            primary=asset,
            related=related,
            annotations=annotations,
            controls=cls.AUDIO_CONTROLS,
            live=False,
        )

    @classmethod
    def live_stream(cls, *, presentation_id: str, title: str, asset: MediaAsset,
                    related: Sequence[MediaAsset] = (), annotations: Mapping[str, Any] = {}) -> MediaPresentation:
        if asset.kind != "live_stream":
            raise ValueError("live presentation requires live_stream asset")
        return MediaPresentation(
            presentation_id=presentation_id,
            title=title,
            primary=asset,
            related=related,
            annotations=annotations,
            controls=cls.LIVE_CONTROLS,
            live=True,
        )

    @classmethod
    def thermal_rgb_fusion(
        cls,
        *,
        presentation_id: str,
        title: str,
        thermal: MediaAsset,
        rgb: MediaAsset,
        overlay: Optional[MediaAsset] = None,
        temperatures: Optional[Mapping[str, Any]] = None,
    ) -> MediaPresentation:
        if thermal.kind not in {"image", "thermal_overlay", "live_stream", "video"}:
            raise ValueError("thermal asset must be visual media")
        if rgb.kind not in {"image", "live_stream", "video"}:
            raise ValueError("rgb asset must be visual media")
        related: List[MediaAsset] = [rgb]
        if overlay is not None:
            if overlay.kind != "thermal_overlay":
                raise ValueError("overlay must be thermal_overlay")
            related.append(overlay)
        return MediaPresentation(
            presentation_id=presentation_id,
            title=title,
            primary=thermal,
            related=tuple(related),
            annotations={"temperatures": dict(temperatures or {}), "fusion": "thermal+rgb"},
            controls=cls.IMAGE_CONTROLS + ("toggle_rgb", "toggle_thermal", "toggle_overlay"),
            live=thermal.kind == "live_stream" or rgb.kind == "live_stream",
        )


class MediaPresentationRegistry:
    """Small in-memory catalog; storage/persistence may be provided by another service."""

    def __init__(self) -> None:
        self._items: Dict[str, MediaPresentation] = {}

    def put(self, presentation: MediaPresentation) -> None:
        presentation.validate()
        self._items[presentation.presentation_id] = presentation

    def get(self, presentation_id: str) -> Optional[MediaPresentation]:
        return self._items.get(presentation_id)

    def list(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._items.values()]

    def remove(self, presentation_id: str) -> None:
        self._items.pop(presentation_id, None)
