"""Summary store — SSOT for agent memory persistence.

Reads and writes analysis summaries as dated Markdown files in
data/summaries/.  This is the single mechanism for building
long-term context across analysis runs.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from vitalis.models import AnalysisSummary

# Default summaries directory — relative to repo root
_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "summaries"


class SummaryStore:
    """Read/write analysis summaries as Markdown files."""

    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory else _DEFAULT_DIR
        self.directory.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────────

    def save(self, summary: AnalysisSummary) -> Path:
        """Persist a summary as `YYYY-MM-DD.md`."""
        path = self._path_for(summary.date)
        content = self._render_markdown(summary)
        path.write_text(content, encoding="utf-8")
        return path

    # ── Read ───────────────────────────────────────────────────────────────

    def load_latest(self) -> Optional[AnalysisSummary]:
        """Load the most recent summary, or None if no summaries exist."""
        files = sorted(self.directory.glob("*.md"), reverse=True)
        # Skip README.md
        files = [f for f in files if f.stem != "README"]
        if not files:
            return None
        return self._parse_markdown(files[0])

    def load_by_date(self, day: date) -> Optional[AnalysisSummary]:
        """Load a summary for a specific date."""
        path = self._path_for(day)
        if not path.exists():
            return None
        return self._parse_markdown(path)

    def list_dates(self) -> list[date]:
        """List all dates that have summaries."""
        files = sorted(self.directory.glob("*.md"))
        dates: list[date] = []
        for f in files:
            if f.stem == "README":
                continue
            try:
                dates.append(date.fromisoformat(f.stem))
            except ValueError:
                continue
        return dates

    def get_context_for_next_run(self) -> str:
        """Convenience: return the context string from the latest summary."""
        latest = self.load_latest()
        return latest.context_for_next_run if latest else ""

    # ── Private ────────────────────────────────────────────────────────────

    def _path_for(self, day: date) -> Path:
        return self.directory / f"{day.isoformat()}.md"

    @staticmethod
    def _render_markdown(summary: AnalysisSummary) -> str:
        """Render an AnalysisSummary to a human-readable Markdown file."""
        recs = "\n".join(
            f"- **[{r.category}]** {r.title} (P{r.priority}): {r.detail}"
            for r in summary.recommendations
        )

        return f"""# Vitalis Health Summary — {summary.date.isoformat()}

**Period**: {summary.period_start.isoformat()} → {summary.period_end.isoformat()}

## Metrics Snapshot

```json
{json.dumps(summary.metrics_snapshot, indent=2)}
```

## Trends

{chr(10).join(f"- {t}" for t in summary.trends)}

## Recommendations

{recs}

## Context for Next Run

{summary.context_for_next_run}

---
<!-- machine-readable block — do not edit -->
```vitalis-meta
{summary.model_dump_json(indent=2)}
```
"""

    @staticmethod
    def _parse_markdown(path: Path) -> Optional[AnalysisSummary]:
        """Parse an AnalysisSummary from a Markdown file.

        Looks for the ```vitalis-meta``` block for reliable deserialization.
        Falls back to None if parsing fails.
        """
        content = path.read_text(encoding="utf-8")
        marker = "```vitalis-meta"
        start = content.find(marker)
        if start == -1:
            return None

        start += len(marker)
        end = content.find("```", start)
        if end == -1:
            return None

        json_str = content[start:end].strip()
        try:
            return AnalysisSummary.model_validate_json(json_str)
        except Exception:
            return None
