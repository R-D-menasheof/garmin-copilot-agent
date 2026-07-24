"""Build and distribute a signed Vitalis Android release through Firebase.

The build is copied outside the OneDrive workspace before Gradle runs. This is
required because OneDrive has previously produced silently corrupted APKs.
Signing secrets stay in ``mobile/android`` and are ignored by Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOBILE_DIR = PROJECT_ROOT / "mobile"
DEFAULT_FIREBASE_APP_ID = "1:667160635189:android:cde5b92ba89292ef12ce7c"
DEFAULT_FIREBASE_PROJECT = "vitalis-ee758"
DEFAULT_FIREBASE_GROUP = "vitalis-users"
DEFAULT_FIREBASE_CREDENTIALS = (
    PROJECT_ROOT / "data/.secrets/fcm-service-account.json"
)
DEFAULT_SIGNING_DIR = PROJECT_ROOT / "data/.secrets/mobile-signing"
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class SigningFiles(NamedTuple):
    """Validated Android signing files."""

    properties: Path
    keystore: Path


def parse_version(version: str, build_number: int) -> tuple[str, int]:
    """Validate a release version and monotonically increasing build number."""
    if not _SEMVER.fullmatch(version):
        raise ValueError("version must be plain SemVer, for example 1.2.3")
    if build_number <= 0:
        raise ValueError("build number must be a positive integer")
    return version, build_number


def _read_properties(path: Path) -> dict[str, str]:
    properties: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()
    return properties


def validate_signing_files(signing_dir: Path) -> SigningFiles:
    """Validate the private release keystore and key.properties file."""
    properties_path = signing_dir / "key.properties"
    keystore_path = signing_dir / "upload-keystore.jks"
    if not properties_path.is_file() or not keystore_path.is_file():
        raise FileNotFoundError(
            "mobile signing secrets are missing: expected key.properties and "
            f"upload-keystore.jks under {signing_dir}"
        )

    properties = _read_properties(properties_path)
    required = {"storePassword", "keyPassword", "keyAlias", "storeFile"}
    missing = sorted(key for key in required if not properties.get(key))
    if missing:
        raise ValueError(
            "key.properties is missing required values: " + ", ".join(missing)
        )
    return SigningFiles(properties=properties_path, keystore=keystore_path)


def validate_firebase_credentials(path: Path, project_id: str) -> Path:
    """Validate that a service-account file belongs to the target project."""
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Firebase service account not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    actual_project = payload.get("project_id")
    if payload.get("type") != "service_account" or actual_project != project_id:
        raise ValueError(
            "Firebase credentials project mismatch: "
            f"expected {project_id!r}, got {actual_project!r}"
        )
    return resolved


def firebase_environment(
    base: dict[str, str],
    credentials: Path,
    config_dir: Path,
) -> dict[str, str]:
    """Return a Firebase CLI environment using private service credentials."""
    env = base.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials.resolve())
    env["XDG_CONFIG_HOME"] = str(config_dir.resolve())
    return env


def build_environment(base: dict[str, str], build_root: Path) -> dict[str, str]:
    """Keep Pub and Gradle caches on the build drive for Kotlin compatibility."""
    root = build_root.resolve()
    pub_cache = root / "pub-cache"
    gradle_home = root / "gradle-cache"
    pub_cache.mkdir(parents=True, exist_ok=True)
    gradle_home.mkdir(parents=True, exist_ok=True)
    env = base.copy()
    env["PUB_CACHE"] = str(pub_cache)
    env["GRADLE_USER_HOME"] = str(gradle_home)
    return env


def firebase_distribution_command(
    *,
    firebase_executable: str,
    artifact: Path,
    notes_file: Path,
    app_id: str,
    project_id: str,
    group: str,
) -> list[str]:
    """Build the Firebase CLI command used to distribute one APK."""
    return [
        firebase_executable,
        "appdistribution:distribute",
        str(artifact),
        "--app",
        app_id,
        "--project",
        project_id,
        "--groups",
        group,
        "--release-notes-file",
        str(notes_file),
    ]


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    printable = " ".join(command)
    print(f"\n> {printable}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _find_executable(explicit: str | None, candidates: list[str]) -> str:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        resolved = shutil.which(explicit)
        if resolved:
            return resolved
        raise FileNotFoundError(f"Executable not found: {explicit}")

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return str(path)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(f"None of these executables were found: {candidates}")


def _default_build_root() -> Path:
    configured = os.environ.get("VITALIS_MOBILE_BUILD_ROOT")
    if configured:
        return Path(configured)
    if os.name == "nt" and Path("Q:/").exists():
        return Path("Q:/vitalis-firebase-release")
    return Path.home() / ".vitalis-build"


def _sync_mobile(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    robocopy = shutil.which("robocopy") if os.name == "nt" else None
    if robocopy:
        result = subprocess.run(
            [
                robocopy,
                str(source),
                str(destination),
                "/MIR",
                "/XD",
                "build",
                ".dart_tool",
                ".gradle",
                "/NFL",
                "/NDL",
                "/NJH",
                "/NP",
                "/R:1",
                "/W:1",
            ],
            check=False,
        )
        if result.returncode > 7:
            raise subprocess.CalledProcessError(result.returncode, result.args)
        return

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("build", ".dart_tool", ".gradle"),
    )


def _verify_critical_files(mobile_dir: Path) -> None:
    required = [
        mobile_dir
        / "android/app/src/main/kotlin/com/vitalis/vitalis/MainActivity.kt",
        mobile_dir / "android/app/google-services.json",
        mobile_dir / "android/key.properties",
        mobile_dir / "android/upload-keystore.jks",
    ]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError(
            "Required build files are missing or empty:\n" + "\n".join(missing)
        )


def _copy_signing_files(signing: SigningFiles, mobile_dir: Path) -> None:
    android_dir = mobile_dir / "android"
    android_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(signing.properties, android_dir / "key.properties")
    shutil.copy2(signing.keystore, android_dir / "upload-keystore.jks")


def _verify_apk_signature(apk: Path, mobile_dir: Path) -> None:
    local_properties = mobile_dir / "android/local.properties"
    if not local_properties.is_file():
        print("Warning: local.properties missing; skipping apksigner verification.")
        return
    properties = _read_properties(local_properties)
    sdk_dir = properties.get("sdk.dir")
    if not sdk_dir:
        print("Warning: sdk.dir missing; skipping apksigner verification.")
        return
    build_tools = Path(sdk_dir.replace("\\\\", "\\")) / "build-tools"
    names = ("apksigner.bat", "apksigner")
    candidates = sorted(
        (path for name in names for path in build_tools.glob(f"*/{name}")),
        reverse=True,
    )
    if not candidates:
        print("Warning: apksigner not found; skipping signature verification.")
        return
    _run([str(candidates[0]), "verify", "--verbose", "--print-certs", str(apk)])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse release arguments."""
    parser = argparse.ArgumentParser(
        description="Build and distribute a signed Vitalis Android release.",
    )
    parser.add_argument("--version", required=True, help="SemVer, e.g. 1.1.0")
    parser.add_argument("--build-number", required=True, type=int)
    parser.add_argument("--notes", required=True, help="Release notes for testers")
    parser.add_argument(
        "--signing-dir",
        type=Path,
        default=DEFAULT_SIGNING_DIR,
    )
    parser.add_argument("--build-root", type=Path, default=_default_build_root())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Downloads",
    )
    parser.add_argument("--flutter")
    parser.add_argument("--firebase")
    parser.add_argument("--firebase-app-id", default=DEFAULT_FIREBASE_APP_ID)
    parser.add_argument("--firebase-project", default=DEFAULT_FIREBASE_PROJECT)
    parser.add_argument("--group", default=DEFAULT_FIREBASE_GROUP)
    parser.add_argument(
        "--firebase-credentials",
        type=Path,
        default=DEFAULT_FIREBASE_CREDENTIALS,
    )
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run tests, build outside OneDrive, verify, and distribute."""
    args = parse_args(argv)
    version, build_number = parse_version(args.version, args.build_number)
    signing = validate_signing_files(args.signing_dir.resolve())
    flutter = _find_executable(
        args.flutter or os.environ.get("VITALIS_FLUTTER"),
        ["Q:/flutter/bin/flutter.bat", "flutter", "flutter.bat"],
    )

    if not args.skip_tests:
        _run([flutter, "test"], cwd=MOBILE_DIR)

    build_mobile = args.build_root.resolve() / "mobile"
    print(f"\nSyncing mobile source to {build_mobile}")
    _sync_mobile(MOBILE_DIR, build_mobile)
    _copy_signing_files(signing, build_mobile)
    _verify_critical_files(build_mobile)

    build_env = build_environment(os.environ.copy(), args.build_root)
    _run([flutter, "pub", "get"], cwd=build_mobile, env=build_env)
    _run(
        [
            flutter,
            "build",
            "apk",
            "--release",
            "--build-name",
            version,
            "--build-number",
            str(build_number),
        ],
        cwd=build_mobile,
        env=build_env,
    )

    built_apk = build_mobile / "build/app/outputs/flutter-apk/app-release.apk"
    if not built_apk.is_file():
        raise FileNotFoundError(f"Flutter did not create {built_apk}")
    _verify_apk_signature(built_apk, build_mobile)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    label = f"{version}+{build_number}"
    artifact = args.output_dir / f"vitalis-{label}.apk"
    notes_file = args.output_dir / f"vitalis-{label}-notes.txt"
    shutil.copy2(built_apk, artifact)
    notes_file.write_text(args.notes.strip() + "\n", encoding="utf-8")
    print(f"\nAPK: {artifact}")
    print(f"SHA256: {_sha256(artifact)}")

    if args.skip_upload:
        print("Firebase upload skipped.")
        return 0

    firebase = _find_executable(
        args.firebase or os.environ.get("FIREBASE_CLI"),
        ["firebase", "firebase.cmd"],
    )
    firebase_credentials = validate_firebase_credentials(
        args.firebase_credentials,
        args.firebase_project,
    )
    firebase_config_dir = args.build_root.resolve() / "firebase-cli-config"
    firebase_config_dir.mkdir(parents=True, exist_ok=True)
    _run(
        firebase_distribution_command(
            firebase_executable=firebase,
            artifact=artifact,
            notes_file=notes_file,
            app_id=args.firebase_app_id,
            project_id=args.firebase_project,
            group=args.group,
        ),
        env=firebase_environment(
            os.environ.copy(),
            firebase_credentials,
            firebase_config_dir,
        ),
    )
    print(f"Distributed {label} to Firebase group '{args.group}'.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Release failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc