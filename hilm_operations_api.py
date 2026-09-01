"""Private Hilm operational API mounted into Ameer runtime."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from kernel.hilm_operations_runtime import HilmOperationsRuntime
from kernel.internal_auth_runtime import principal_from_headers


router = APIRouter(prefix="/internal/hilm", tags=["hilm-operations"])
DATA_ROOT = Path(os.getenv("AMEER_DATA_DIR", ".ameer")).resolve()
if DATA_ROOT.name != ".ameer":
    DATA_ROOT = DATA_ROOT / ".ameer"
RUNTIME = HilmOperationsRuntime(DATA_ROOT / "hilm_operations.json")


def _require(request: Request, *roles: str, scope: str = "") -> str:
    try:
        principal = principal_from_headers(request.headers, required_roles=roles, required_scope=scope)
        return principal.role
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/health")
def health(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "reception", scope="hilm:read")
    return {"ok": True, "state_path": str(RUNTIME.path), "offline_pending": RUNTIME.operations_report()["offline_pending"]}


@router.post("/stock/items")
async def upsert_stock(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", scope="hilm:manage")
    p = await request.json()
    try:
        return RUNTIME.upsert_stock_item(str(p["item_id"]), name=str(p["name"]), quantity=float(p["quantity"]), unit=str(p["unit"]), reorder_level=float(p.get("reorder_level", 0)))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/services/recipes")
async def set_recipe(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", scope="hilm:manage")
    p = await request.json()
    try:
        return {"service_id": str(p["service_id"]), "consumables": RUNTIME.set_service_recipe(str(p["service_id"]), p.get("consumables") or {})}
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/services/complete")
async def complete_service(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "reception", scope="hilm:pos")
    p = await request.json()
    try:
        return RUNTIME.complete_service(
            transaction_id=str(p["transaction_id"]), booking_id=str(p["booking_id"]), customer_id=str(p["customer_id"]),
            service_id=str(p["service_id"]), employee_id=str(p["employee_id"]), sale_amount=float(p["sale_amount"]),
            commission_rate=float(p.get("commission_rate", 0)), source=str(p.get("source") or "web"), online=bool(p.get("online", True)),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing:{exc}") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/ratings")
async def rating(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", "reception", scope="hilm:pos")
    p = await request.json()
    try:
        return RUNTIME.add_rating(transaction_id=str(p["transaction_id"]), employee_id=str(p["employee_id"]), score=int(p["score"]), comment=str(p.get("comment") or ""))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/incidents")
async def incident(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", scope="hilm:manage")
    p = await request.json()
    try:
        return RUNTIME.record_incident(
            incident_id=str(p["incident_id"]), kind=str(p["kind"]), item_id=str(p.get("item_id") or ""), quantity=float(p.get("quantity", 0)),
            employee_id=str(p.get("employee_id") or ""), department_id=str(p.get("department_id") or ""), verified=bool(p.get("verified", False)),
            evidence_ref=str(p.get("evidence_ref") or ""), notes=str(p.get("notes") or ""),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync/{transaction_id}")
def mark_synced(transaction_id: str, request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", scope="hilm:sync")
    try:
        return RUNTIME.mark_synced(transaction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/operations")
def report(request: Request) -> Dict[str, Any]:
    _require(request, "founder", "ameer", "admin", scope="hilm:reports")
    return RUNTIME.operations_report()
