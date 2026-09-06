"""
ameer_server.py
===============
Server facade that preserves the established Shadow System application and adds
private Extended Senses runtime endpoints.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from dataclasses import asdict

from fastapi import Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from ameer_server_base import *  # noqa: F401,F403
import ameer_server_base as _base

app = _base.app
KERNEL = _base.KERNEL


def __getattr__(name):
    return getattr(_base, name)


def _senses_runtime():
    kernel = KERNEL
    runtime = getattr(kernel, "senses", None) if kernel is not None else None
    if runtime is None:
        raise HTTPException(status_code=503, detail="extended_senses_runtime_unavailable")
    return runtime


def _require_senses_access(x_ameer_senses_token: str | None) -> None:
    expected = os.getenv("AMEER_SENSES_ACCESS_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="senses_access_token_not_configured")
    supplied = (x_ameer_senses_token or "").strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid_senses_access_token")


@app.get("/ui/senses")
def senses_snapshot(x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    return _senses_runtime().snapshot()


@app.get("/ui/senses/sensors")
def senses_sensors(x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    return _senses_runtime().sensor_hub.health_snapshot()


@app.get("/ui/senses/presentations")
def senses_presentations(x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    runtime = _senses_runtime()
    live = runtime.presentations.list()
    return {"presentations": live or runtime.catalog.presentations()}


@app.get("/ui/senses/sensors/{sensor_id}/frame")
def senses_last_frame(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    runtime = _senses_runtime()
    frame = runtime.last_frame(sensor_id)
    if frame is not None:
        return asdict(frame)
    persisted = runtime.persisted_last_frame(sensor_id)
    if persisted is not None:
        return persisted
    raise HTTPException(status_code=404, detail="sensor_frame_not_available")


@app.get("/ui/senses/events")
def senses_events(after: int = 0, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    return {"events": _senses_runtime().events_since(max(after, 0))}


@app.get("/ui/senses/events/stream")
async def senses_event_stream(
    request: Request,
    after: int = 0,
    x_ameer_senses_token: str | None = Header(default=None),
):
    """Owner-only Server-Sent Events feed with replay from the requested event id."""
    _require_senses_access(x_ameer_senses_token)
    runtime = _senses_runtime()

    async def generate():
        cursor = max(after, 0)
        idle_ticks = 0
        while not await request.is_disconnected():
            events = runtime.events_since(cursor)
            if events:
                for event in events:
                    cursor = max(cursor, int(event.get("event_id", 0)))
                    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                    yield f"id: {cursor}\nevent: {event.get('event_type', 'message')}\ndata: {payload}\n\n"
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 30:
                    yield ": keepalive\n\n"
                    idle_ticks = 0
            await asyncio.sleep(0.5)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.get("/ui/senses/calibration")
def senses_calibration_list(x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    return {"calibrations": _senses_runtime().calibration.list()}


@app.get("/ui/senses/calibration/{sensor_id}")
def senses_calibration_get(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    item = _senses_runtime().get_calibration(sensor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="sensor_calibration_not_available")
    return item


@app.put("/ui/senses/calibration/{sensor_id}")
async def senses_calibration_set(sensor_id: str, request: Request, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="calibration_payload_must_be_object")
    return _senses_runtime().set_calibration(sensor_id, payload)


@app.post("/ui/senses/sensors/{sensor_id}/connect")
def senses_connect(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    try:
        return _senses_runtime().connect_sensor(sensor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"sensor_connect_failed: {exc}") from exc


@app.post("/ui/senses/sensors/{sensor_id}/disconnect")
def senses_disconnect(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    try:
        return _senses_runtime().disconnect_sensor(sensor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"sensor_disconnect_failed: {exc}") from exc


@app.post("/ui/senses/sensors/{sensor_id}/read")
def senses_read(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    try:
        return asdict(_senses_runtime().read_sensor(sensor_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"sensor_read_failed: {exc}") from exc
