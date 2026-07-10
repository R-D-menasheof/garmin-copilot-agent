"""FCM push notification sender — Phase 7 (SSOT for sending notifications).

Sends push notifications to users' registered device tokens via the Firebase
Cloud Messaging (FCM) HTTP v1 API. Authenticates with a Firebase service
account using the OAuth2 JWT-bearer flow signed with PyJWT (RS256) — no
``google-auth`` dependency. Safe no-op when unconfigured, so callers can invoke
it unconditionally.

Config (Function app settings / owner env):
- ``FCM_PROJECT_ID``            — the Firebase project id.
- ``FCM_SERVICE_ACCOUNT_JSON``  — the service account JSON (as a string), OR
- ``FCM_SERVICE_ACCOUNT_FILE``  — a path to the service account JSON file.
"""

from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"


def _access_token(service_account: dict) -> str:
    """Mint an OAuth2 access token for FCM from a service account (JWT bearer)."""
    import httpx
    import jwt  # PyJWT

    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": service_account["client_email"],
            "scope": _FCM_SCOPE,
            "aud": _TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        },
        service_account["private_key"],
        algorithm="RS256",
    )
    resp = httpx.post(
        _TOKEN_URL,
        data={"grant_type": _JWT_BEARER, "assertion": assertion},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _send_one(
    project_id: str,
    access_token: str,
    token: str,
    title: str,
    body: str,
    data: dict | None,
) -> bool:
    """Send a single FCM v1 message. Returns True on HTTP 200."""
    import httpx

    resp = httpx.post(
        f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": {k: str(v) for k, v in (data or {}).items()},
            }
        },
        timeout=15.0,
    )
    if resp.status_code == 200:
        return True
    logger.warning("FCM send failed (%s): %s", resp.status_code, resp.text[:200])
    return False


class NotificationSender:
    """Sends FCM push notifications. No-op unless configured with credentials."""

    def __init__(
        self,
        project_id: str | None = None,
        service_account: dict | None = None,
    ) -> None:
        self._project_id = project_id or os.environ.get("FCM_PROJECT_ID")
        if service_account is None:
            raw = os.environ.get("FCM_SERVICE_ACCOUNT_JSON")
            if raw:
                service_account = json.loads(raw)
            else:
                path = os.environ.get("FCM_SERVICE_ACCOUNT_FILE")
                if path and os.path.exists(path):
                    with open(path, encoding="utf-8") as handle:
                        service_account = json.load(handle)
        self._sa = service_account

    @property
    def configured(self) -> bool:
        """True when both a project id and service account are available."""
        return bool(self._project_id and self._sa)

    def send(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> int:
        """Send a notification to each token. Returns the count delivered."""
        if not self.configured or not tokens:
            return 0
        access = _access_token(self._sa)
        return sum(
            1
            for token in tokens
            if _send_one(self._project_id, access, token, title, body, data)
        )


def notify_report_ready(store, date_iso: str, sender: NotificationSender | None = None) -> int:
    """Notify a user's devices that a new health report is ready.

    Args:
        store: A ``BlobStore`` scoped to the target user (for its push tokens).
        date_iso: The report date (ISO string) to reference in the message.
        sender: Optional pre-built sender (for tests / reuse).

    Returns:
        The number of devices successfully notified (0 if unconfigured / none).
    """
    sender = sender or NotificationSender()
    if not sender.configured:
        logger.info("Notifications not configured; skipping report-ready push.")
        return 0
    tokens = [t.token for t in store.load_push_tokens()]
    if not tokens:
        return 0
    return sender.send(
        tokens,
        'דו"ח בריאות חדש מוכן',
        f"הניתוח ({date_iso}) מוכן לצפייה באפליקציה",
        data={"type": "report", "date": date_iso},
    )
