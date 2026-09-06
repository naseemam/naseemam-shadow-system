from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.media_presentation import MediaAsset, MediaPresentationBuilder, MediaPresentationRegistry


def test_image_presentation_controls():
    asset = MediaAsset(
        asset_id="img-1",
        kind="image",
        source_sensor_id="rgb-1",
        uri="memory://image/1",
        mime_type="image/png",
        width=1920,
        height=1080,
    )
    card = MediaPresentationBuilder.image(
        presentation_id="p-1",
        title="RGB frame",
        asset=asset,
    )
    data = card.to_dict()
    assert data["primary"]["kind"] == "image"
    assert "zoom" in data["controls"]
    assert data["live"] is False


def test_audio_can_include_waveform_and_spectrogram():
    audio = MediaAsset(
        asset_id="audio-1",
        kind="audio",
        source_sensor_id="ultra-1",
        uri="memory://audio/1",
        mime_type="audio/wav",
        sample_rate_hz=192000,
    )
    waveform = MediaAsset(
        asset_id="wave-1",
        kind="waveform",
        source_sensor_id="ultra-1",
        uri="memory://waveform/1",
        mime_type="application/json",
    )
    spectrogram = MediaAsset(
        asset_id="spec-1",
        kind="spectrogram",
        source_sensor_id="ultra-1",
        uri="memory://spectrogram/1",
        mime_type="image/png",
    )
    card = MediaPresentationBuilder.audio(
        presentation_id="p-audio",
        title="Ultrasonic capture",
        asset=audio,
        related=(waveform, spectrogram),
        annotations={"converted_for_human_listening": True},
    )
    data = card.to_dict()
    assert len(data["related"]) == 2
    assert data["annotations"]["converted_for_human_listening"] is True
    assert "play" in data["controls"]


def test_live_stream_is_marked_live():
    stream = MediaAsset(
        asset_id="live-1",
        kind="live_stream",
        source_sensor_id="thermal-1",
        uri="rtsp://example.invalid/thermal",
        mime_type="application/x-rtsp",
    )
    card = MediaPresentationBuilder.live_stream(
        presentation_id="p-live",
        title="Thermal live stream",
        asset=stream,
    )
    assert card.to_dict()["live"] is True


def test_thermal_rgb_fusion_keeps_original_layers():
    thermal = MediaAsset(
        asset_id="thermal-1-frame",
        kind="image",
        source_sensor_id="thermal-1",
        uri="memory://thermal/1",
        mime_type="image/png",
    )
    rgb = MediaAsset(
        asset_id="rgb-1-frame",
        kind="image",
        source_sensor_id="rgb-1",
        uri="memory://rgb/1",
        mime_type="image/jpeg",
    )
    overlay = MediaAsset(
        asset_id="overlay-1",
        kind="thermal_overlay",
        source_sensor_id="thermal-1",
        uri="memory://overlay/1",
        mime_type="image/png",
    )
    card = MediaPresentationBuilder.thermal_rgb_fusion(
        presentation_id="p-fusion",
        title="Thermal + RGB",
        thermal=thermal,
        rgb=rgb,
        overlay=overlay,
        temperatures={"min_c": 22.0, "max_c": 35.5},
    )
    data = card.to_dict()
    assert data["primary"]["asset_id"] == "thermal-1-frame"
    assert {x["asset_id"] for x in data["related"]} == {"rgb-1-frame", "overlay-1"}
    assert data["annotations"]["fusion"] == "thermal+rgb"
    assert "toggle_overlay" in data["controls"]


def test_registry_roundtrip():
    asset = MediaAsset(
        asset_id="vid-1",
        kind="video",
        source_sensor_id="rgb-1",
        uri="memory://video/1",
        mime_type="video/mp4",
        duration_ms=1200,
    )
    card = MediaPresentationBuilder.video(
        presentation_id="p-video",
        title="Recorded clip",
        asset=asset,
    )
    registry = MediaPresentationRegistry()
    registry.put(card)
    assert registry.get("p-video") is not None
    assert registry.list()[0]["primary"]["kind"] == "video"
    registry.remove("p-video")
    assert registry.get("p-video") is None
