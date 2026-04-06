"""Shared auth helper for API endpoints."""

from __future__ import annotations

import os


def verify_api_key(req) -> bool:
    """Check x-api-key header against stored key.

    Args:
        req: Azure Functions HttpRequest (or mock with .headers dict).

    Returns:
        True if the key matches, False otherwise.
    """
    expected = os.environ.get("VITALIS_API_KEY", "")
    actual = req.headers.get("x-api-key", "")
    return bool(expected and actual == expected)
