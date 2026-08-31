"""Final composed Ameer application for web/local operational services."""
from __future__ import annotations

from ameer_proactive_bootstrap import app
from hilm_alerts_api import router as hilm_alerts_router

app.include_router(hilm_alerts_router)
