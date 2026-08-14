from __future__ import annotations

import base64
import json
import os
from email.message import EmailMessage
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GoogleWorkspaceConfigurationError(RuntimeError):
    pass


class GoogleWorkspaceClient:
    """Gmail + Google Calendar client for Ameer using OAuth refresh tokens.

    Secrets are read only from environment variables:
      AMEER_GOOGLE_CLIENT_ID
      AMEER_GOOGLE_CLIENT_SECRET
      AMEER_GOOGLE_REFRESH_TOKEN
      AMEER_GOOGLE_USER (defaults to 'me')
      AMEER_GOOGLE_CALENDAR_ID (defaults to 'primary')
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
    CALENDAR_API = "https://www.googleapis.com/calendar/v3"

    def __init__(self) -> None:
        self.client_id = (os.getenv("AMEER_GOOGLE_CLIENT_ID") or "").strip()
        self.client_secret = (os.getenv("AMEER_GOOGLE_CLIENT_SECRET") or "").strip()
        self.refresh_token = (os.getenv("AMEER_GOOGLE_REFRESH_TOKEN") or "").strip()
        self.user = (os.getenv("AMEER_GOOGLE_USER") or "me").strip()
        self.calendar_id = (os.getenv("AMEER_GOOGLE_CALENDAR_ID") or "primary").strip()

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def _require(self) -> None:
        if not self.configured:
            raise GoogleWorkspaceConfigurationError(
                "Google Workspace requires AMEER_GOOGLE_CLIENT_ID, "
                "AMEER_GOOGLE_CLIENT_SECRET, and AMEER_GOOGLE_REFRESH_TOKEN."
            )

    def _access_token(self) -> str:
        self._require()
        data = urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = Request(self.TOKEN_URL, data=data, method="POST")
        with urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        token = payload.get("access_token")
        if not token:
            raise GoogleWorkspaceConfigurationError("Google OAuth refresh did not return an access token")
        return str(token)

    def _request(self, method: str, url: str, payload: Optional[dict] = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    # Gmail
    def search_messages(self, query: str = "", *, max_results: int = 20) -> List[Dict[str, Any]]:
        params = urlencode({"q": query, "maxResults": int(max_results)})
        result = self._request("GET", f"{self.GMAIL_API}/users/{self.user}/messages?{params}")
        return list(result.get("messages") or [])

    def get_message(self, message_id: str, *, format: str = "metadata") -> Dict[str, Any]:
        params = urlencode({"format": format})
        return self._request(
            "GET", f"{self.GMAIL_API}/users/{self.user}/messages/{message_id}?{params}"
        )

    def send_email(self, to: str, subject: str, body: str, *, cc: str = "", bcc: str = "") -> Dict[str, Any]:
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
        return self._request(
            "POST", f"{self.GMAIL_API}/users/{self.user}/messages/send", {"raw": raw}
        )

    # Calendar
    def list_events(
        self,
        *,
        time_min: str,
        time_max: str = "",
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "timeMin": time_min,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": int(max_results),
        }
        if time_max:
            params["timeMax"] = time_max
        result = self._request(
            "GET",
            f"{self.CALENDAR_API}/calendars/{self.calendar_id}/events?{urlencode(params)}",
        )
        return list(result.get("items") or [])

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        *,
        timezone: str = "Asia/Riyadh",
        description: str = "",
        attendees: Optional[List[str]] = None,
        location: str = "",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        if description:
            payload["description"] = description
        if location:
            payload["location"] = location
        if attendees:
            payload["attendees"] = [{"email": email} for email in attendees]
        return self._request(
            "POST", f"{self.CALENDAR_API}/calendars/{self.calendar_id}/events", payload
        )

    def update_event(self, event_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        return self._request(
            "PATCH",
            f"{self.CALENDAR_API}/calendars/{self.calendar_id}/events/{event_id}",
            changes,
        )

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        return self._request(
            "DELETE", f"{self.CALENDAR_API}/calendars/{self.calendar_id}/events/{event_id}"
        )
