from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "release_mobile.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_mobile", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_version_accepts_semver_and_positive_build_number() -> None:
    release = _load_module()

    assert release.parse_version("1.2.3", 7) == ("1.2.3", 7)


@pytest.mark.parametrize(
    ("version", "build_number"),
    [("1.2", 2), ("1.2.3+4", 2), ("v1.2.3", 2), ("1.2.3", 0)],
)
def test_parse_version_rejects_invalid_values(
    version: str,
    build_number: int,
) -> None:
    release = _load_module()

    with pytest.raises(ValueError):
        release.parse_version(version, build_number)


def test_firebase_command_targets_vitalis_testers(tmp_path: Path) -> None:
    release = _load_module()
    artifact = tmp_path / "vitalis-1.2.3+7.apk"
    notes = tmp_path / "release-notes.txt"

    command = release.firebase_distribution_command(
        firebase_executable="firebase.cmd",
        artifact=artifact,
        notes_file=notes,
        app_id="firebase-app-id",
        project_id="firebase-project",
        group="vitalis-users",
    )

    assert command == [
        "firebase.cmd",
        "appdistribution:distribute",
        str(artifact),
        "--app",
        "firebase-app-id",
        "--project",
        "firebase-project",
        "--groups",
        "vitalis-users",
        "--release-notes-file",
        str(notes),
    ]


def test_validate_signing_files_resolves_keystore(tmp_path: Path) -> None:
    release = _load_module()
    signing_dir = tmp_path / "mobile-signing"
    signing_dir.mkdir()
    (signing_dir / "upload-keystore.jks").write_bytes(b"keystore")
    (signing_dir / "key.properties").write_text(
        "storePassword=secret\n"
        "keyPassword=secret\n"
        "keyAlias=vitalis-upload\n"
        "storeFile=../upload-keystore.jks\n",
        encoding="utf-8",
    )

    files = release.validate_signing_files(signing_dir)

    assert files.keystore == signing_dir / "upload-keystore.jks"
    assert files.properties == signing_dir / "key.properties"


def test_validate_signing_files_rejects_missing_secret(tmp_path: Path) -> None:
    release = _load_module()

    with pytest.raises(FileNotFoundError, match="mobile signing secrets"):
        release.validate_signing_files(tmp_path / "missing")


def test_validate_firebase_credentials_checks_project(tmp_path: Path) -> None:
    release = _load_module()
    credentials = tmp_path / "firebase.json"
    credentials.write_text(
        json.dumps({"type": "service_account", "project_id": "vitalis-ee758"}),
        encoding="utf-8",
    )

    assert release.validate_firebase_credentials(
        credentials,
        "vitalis-ee758",
    ) == credentials.resolve()


def test_validate_firebase_credentials_rejects_wrong_project(
    tmp_path: Path,
) -> None:
    release = _load_module()
    credentials = tmp_path / "firebase.json"
    credentials.write_text(
        json.dumps({"type": "service_account", "project_id": "wrong-project"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="wrong-project"):
        release.validate_firebase_credentials(credentials, "vitalis-ee758")


def test_firebase_environment_sets_credentials_without_mutating_input(
    tmp_path: Path,
) -> None:
    release = _load_module()
    credentials = tmp_path / "firebase.json"
    config_dir = tmp_path / "firebase-cli-config"
    original = {"PATH": "test"}

    result = release.firebase_environment(original, credentials, config_dir)

    assert result["GOOGLE_APPLICATION_CREDENTIALS"] == str(credentials.resolve())
    assert result["XDG_CONFIG_HOME"] == str(config_dir.resolve())
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in original
    assert "XDG_CONFIG_HOME" not in original


def test_build_environment_keeps_caches_under_build_root(tmp_path: Path) -> None:
    release = _load_module()
    original = {"PATH": "test"}

    result = release.build_environment(original, tmp_path)

    assert result["PUB_CACHE"] == str((tmp_path / "pub-cache").resolve())
    assert result["GRADLE_USER_HOME"] == str(
        (tmp_path / "gradle-cache").resolve()
    )
    assert "PUB_CACHE" not in original
    assert "GRADLE_USER_HOME" not in original


def test_android_release_uses_private_signing_config() -> None:
    gradle = (PROJECT_ROOT / "mobile/android/app/build.gradle").read_text(
        encoding="utf-8"
    )

    assert 'rootProject.file("key.properties")' in gradle
    assert "signingConfigs.release" in gradle
    assert "signingConfig = signingConfigs.debug" not in gradle


def test_signing_secrets_are_ignored() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "mobile/android/key.properties" in gitignore
    assert "mobile/android/upload-keystore.jks" in gitignore
