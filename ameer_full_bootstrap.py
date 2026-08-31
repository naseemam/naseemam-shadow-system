"""Final composed Ameer application for web/local operational services."""
from __future__ import annotations

import asyncio

from ameer_proactive_bootstrap import app
from hilm_alerts_api import ALERTS, router as hilm_alerts_router
from hilm_operations_api import RUNTIME as HILM_OPERATIONS
from kernel.hilm_operational_alert_bridge import sync_operations_to_alerts

app.include_router(hilm_alerts_router)


async def _hilm_alert_monitor() -> None:
    while True:
        try:
            sync_operations_to_alerts(HILM_OPERATIONS, ALERTS)
        except Exception:
            pass
        await asyncio.sleep(30)


@app.on_event("startup")
async def start_hilm_alert_monitor():
    sync_operations_to_alerts(HILM_OPERATIONS, ALERTS)
    app.state.hilm_alert_monitor_task = asyncio.create_task(_hilm_alert_monitor())


@app.on_event("shutdown")
async def stop_hilm_alert_monitor():
    task = getattr(app.state, "hilm_alert_monitor_task", None)
    if task:
        task.cancel()
