"""Shared helpers for owner-operated per-user cloud operations (Phase 6).

The owner holds the master Azure Storage connection string and reads/writes
any user's data directly via ``BlobStore(user_id=...)`` — never through the
API. This module wires the import path, resolves the connection string, and
lists registered cloud users.

Requires the master connection string in the environment:
    $env:AZURE_STORAGE_CONNECTION_STRING = (az storage account \
        show-connection-string -g rg-vitalis -n stvitalisdata \
        --query connectionString -o tsv)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from uuid import UUID

# api/ on sys.path so ``shared.blob_store`` (the SSOT for blob ops) and its
# internal ``vitalis.models`` imports resolve exactly as in the deployed
# Azure Function.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_API_DIR = _PROJECT_ROOT / "api"
_SRC_DIR = _PROJECT_ROOT / "src"
for path in (str(_SRC_DIR), str(_API_DIR)):
    while path in sys.path:
        sys.path.remove(path)
sys.path.insert(0, str(_SRC_DIR))
sys.path.insert(1, str(_API_DIR))

from shared.blob_store import BlobStore  # noqa: E402


def normalize_user_id(user_id: str) -> str:
    """Validate an Entra object id or a safe legacy user key."""
    value = user_id.strip()
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value):
            return value
        raise ValueError(f"Invalid user_id: {user_id!r}")


def user_data_directory(user_id: str) -> Path:
    """Return the local staging directory for one user."""
    return _PROJECT_ROOT / "data" / "users" / normalize_user_id(user_id)


def user_reports_directory(user_id: str) -> Path:
    """Return the local report directory for one user."""
    return user_data_directory(user_id) / "reports"


def user_garmin_token_directory(user_id: str) -> Path:
    """Return the isolated Garmin OAuth-token directory for one user."""
    return user_data_directory(user_id) / ".garmin_tokens"


def user_garmin_sync_directory(user_id: str) -> Path:
    """Return the isolated raw Garmin sync directory for one user."""
    return user_data_directory(user_id) / "synced"


def connection_string() -> str:
    """Return the master storage connection string from the environment."""
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise SystemExit(
            "AZURE_STORAGE_CONNECTION_STRING is not set. Set it first, e.g.:\n"
            "  $env:AZURE_STORAGE_CONNECTION_STRING = "
            "(az storage account show-connection-string -g rg-vitalis "
            "-n stvitalisdata --query connectionString -o tsv)"
        )
    return conn


def get_store(user_id: str) -> BlobStore:
    """Return a BlobStore scoped to ``user_id`` using the master connection."""
    return BlobStore(
        connection_string=connection_string(),
        user_id=normalize_user_id(user_id),
    )


def list_users() -> list[dict[str, str]]:
    """List registered cloud users (one per ``users/{id}/profile.json``)."""
    from azure.storage.blob import BlobServiceClient

    svc = BlobServiceClient.from_connection_string(connection_string())
    container = svc.get_container_client("vitalis-data")
    users: list[dict[str, str]] = []
    for blob in container.list_blobs(name_starts_with="users/"):
        parts = blob.name.split("/")
        if len(parts) == 3 and parts[2] == "profile.json":
            uid = parts[1]
            profile = get_store(uid).load_profile()
            users.append(
                {
                    "user_id": uid,
                    "display_name": profile.display_name if profile else "",
                    "email": profile.email if profile else "",
                }
            )
    return users
