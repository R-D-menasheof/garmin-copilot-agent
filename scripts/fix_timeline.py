"""One-shot script to fix timeline events via PUT /api/v1/timeline.

Loads all events, fixes the lifestyle event text, removes duplicates,
and saves back via PUT. Requires the PUT endpoint to be deployed.

Can also be run with --via-post to clear and rebuild (slower but works
without PUT endpoint).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vitalis.fix_timeline")


def main() -> int:
    url = os.environ.get("VITALIS_API_URL", "https://func-vitalis-api.azurewebsites.net/api")
    key = os.environ.get("VITALIS_API_KEY", "")
    headers = {"x-api-key": key, "Content-Type": "application/json"}

    # Load all events
    resp = httpx.get(f"{url}/v1/timeline", headers=headers, timeout=30)
    resp.raise_for_status()
    events = resp.json()["events"]
    logger.info("Loaded %d events", len(events))

    # Fix and deduplicate
    fixed: list[dict] = []
    seen: set[str] = set()
    for e in events:
        eid = f"{e['date']}_{e['category']}_{e.get('title_he', '')[:15]}"
        if eid in seen:
            logger.info("  Skip duplicate: %s", eid)
            continue
        seen.add(eid)

        # Fix the wrong lifestyle event text
        if e.get("date") == "2026-03-01" and e.get("category") == "lifestyle":
            e["title_he"] = "הפחתת שתייה מתוקה"
            e["detail_he"] = (
                "הפחתה משמעותית של משקאות ממותקים + מגנזיום יומי. "
                "עדיין שותה בסופשים ובחגים."
            )
            logger.info("  Fixed: %s %s", e["date"], e["category"])

        fixed.append(e)

    logger.info("Final events: %d", len(fixed))
    for e in fixed:
        logger.info("  %s | %s | %s", e["date"], e["category"], e.get("title_he", ""))

    # Save via PUT
    put_resp = httpx.put(
        f"{url}/v1/timeline",
        content=json.dumps({"events": fixed}, ensure_ascii=False),
        headers=headers,
        timeout=30,
    )
    if put_resp.status_code == 200:
        logger.info("Successfully saved %d events via PUT", len(fixed))
        return 0
    else:
        logger.error("PUT failed: %d %s", put_resp.status_code, put_resp.text)
        return 1


if __name__ == "__main__":
    sys.exit(main())
