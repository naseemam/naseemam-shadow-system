from __future__ import annotations

import uuid

from fastapi import HTTPException, Request


def install_friendly_room_patch(app, server_module) -> None:
    """Replace the legacy canned /friendly-chat endpoint in-place."""
    from kernel.friendly_room_runtime import FriendlyRoomRuntime

    runtime = FriendlyRoomRuntime(server_module.EXECUTIVE_BRAIN)
    old_route = next(
        (
            route for route in list(app.router.routes)
            if getattr(route, "path", None) == "/friendly-chat"
            and "POST" in (getattr(route, "methods", set()) or set())
        ),
        None,
    )
    if old_route is not None:
        app.router.routes.remove(old_route)

    @app.post("/friendly-chat")
    async def context_led_friendly_chat(request: Request):
        request_id = str(uuid.uuid4())
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        query = str((payload or {}).get("query") or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Empty query")

        # Room isolation is about side effects, not policing Ameer's language.
        # Friendly chat never dispatches workers or performs external execution.
        reply = runtime.reply(query)
        return server_module.utf8_json_response({
            "status": "completed",
            "room": "friendly",
            "reply": reply,
            "message": reply,
            "conversation_mode": "context_led",
            "template_driven": False,
            "execution": {
                "started": False,
                "external_effect": False,
                "worker_dispatch": False,
            },
            "request_id": request_id,
        })

    app.state.friendly_room_runtime = runtime
