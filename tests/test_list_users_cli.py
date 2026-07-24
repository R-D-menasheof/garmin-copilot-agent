from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

import json

import list_users as cli  # noqa: E402


def test_main_prints_hebrew_user(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "list_users",
        lambda: [
            {
                "user_id": "11111111-1111-4111-8111-111111111111",
                "display_name": "משתמשת בדיקה",
                "email": "user@example.com",
            }
        ],
    )

    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert "משתמשת בדיקה" in output


def test_main_prints_machine_readable_json(monkeypatch, capsys) -> None:
    users = [
        {
            "user_id": "roei",
            "display_name": "רועי",
            "email": "user@example.com",
        }
    ]
    monkeypatch.setattr(cli, "list_users", lambda: users)

    assert cli.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == users


def test_entra_only_excludes_legacy_user(monkeypatch, capsys) -> None:
    users = [
        {
            "user_id": "22222222-2222-4222-8222-222222222222",
            "display_name": "רועי",
            "email": "user@example.com",
        },
        {"user_id": "roei", "display_name": "Roei", "email": ""},
    ]
    monkeypatch.setattr(cli, "list_users", lambda: users)

    assert cli.main(["--json", "--entra-only"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert [user["user_id"] for user in result] == [
        "22222222-2222-4222-8222-222222222222"
    ]
