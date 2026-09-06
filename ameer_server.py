"""
ameer_server.py
===============
Server facade that preserves the established Shadow System application and adds
private Extended Senses runtime endpoints.

The original server is preserved in ameer_server_base.py. Existing routes and
public imports remain available, while this file mounts the senses surface used
by the owner-facing Shadow System UI.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import asdict

from fastapi import Header, HTTPException

from ameer_server_base import *  # noqa: F401,F403
import ameer_server_base as _base

app = _base.app
KERNEL = _base.KERNEL


def __getattr__(name):
    """Preserve access to names that are intentionally private in the base module."""
    return getattr(_base, name)


def _senses_runtime():
    kernel = KERNEL
    runtime = getattr(kernel, "senses", None) if kernel is not None else None
    if runtime is None:
        raise HTTPException(status_code=503, detail="extended_senses_runtime_unavailable")
    return runtime


def _require_senses_access(x_ameer_senses_token: str | None) -> None:
    """Protect physical-sensor data and controls with a dedicated owner token.

    The token is configured only through AMEER_SENSES_ACCESS_TOKEN and is never
    embedded in source or returned by an endpoint.
    """
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
    return {
        "presentations": _senses_runtime().presentations.list(),
    }


@app.get("/ui/senses/sensors/{sensor_id}/frame")
def senses_last_frame(sensor_id: str, x_ameer_senses_token: str | None = Header(default=None)):
    _require_senses_access(x_ameer_senses_token)
    frame = _senses_runtime().last_frame(sensor_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="sensor_frame_not_available")
    return asdict(frame)


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
