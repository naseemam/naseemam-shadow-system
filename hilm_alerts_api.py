"""Private Hilm alert center API mounted into Ameer runtime."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from kernel.hilm_alert_center_runtime import HilmAlertCenterRuntime
from kernel.internal_auth_runtime import principal_from_headers

router = APIRouter(prefix="/internal/hilm/alerts", tags=["hilm-alerts"])
DATA_ROOT = Path(os.getenv("AMEER_DATA_DIR", ".ameer")).resolve()
if DATA_ROOT.name != ".ameer":
    DATA_ROOT = DATA_ROOT / ".ameer"
ALERTS = HilmAlertCenterRuntime(DATA_ROOT / "hilm_alerts.json")


def _require(request: Request, *roles: str, scope: str = "") -> str:
    try:
        principal = principal_from_headers(request.headers, required_roles=roles, required_scope=scope)
        return principal.role
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("")
def list_alerts(request: Request, category: str = "", severity: str = "", status: str = "", department_id: str = "", employee_id: str = "") -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "nada", scope="hilm:alerts:read")
    return {"alerts": ALERTS.list_alerts(category=category, severity=severity, status=status, department_id=department_id, employee_id=employee_id)}


@router.post("")
async def create_alert(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "nada", scope="hilm:alerts:write")
    p = await request.json()
    try:
        return ALERTS.create_alert(
            category=str(p["category"]), title=str(p["title"]), message=str(p["message"]),
            severity=str(p.get("severity") or "normal"), department_id=str(p.get("department_id") or ""),
            employee_id=str(p.get("employee_id") or ""), item_id=str(p.get("item_id") or ""),
            assignee=str(p.get("assignee") or "nada"), due_at=str(p.get("due_at") or ""),
            root_cause_key=str(p.get("root_cause_key") or ""), source_ref=str(p.get("source_ref") or ""),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{alert_id}/status")
async def transition(alert_id: str, request: Request) -> Dict[str, Any]:
    actor = _require(request, "founder", "ameer", "admin", "nada", scope="hilm:alerts:write")
    p = await request.json()
    try:
        return ALERTS.transition(alert_id, str(p["status"]), actor=actor, action=str(p.get("action") or ""))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ameer-review")
async def ameer_review(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", scope="hilm:alerts:review")
    p = await request.json()
    return {"reviewed": ALERTS.ameer_review(p.get("alert_ids") or [], review_note=str(p.get("review_note") or ""))}


@router.get("/report")
def report(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "nada", scope="hilm:reports")
    return ALERTS.printable_report()


@router.get("/purchase-digest-source")
def purchase_digest_source(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", scope="hilm:alerts:review")
    return ALERTS.purchase_digest_source()
