---
name: release-vitalis-mobile
description: "Build, sign, verify, and distribute the Vitalis Flutter Android app through Firebase App Distribution. Use when: release mobile app, publish APK, distribute Android build, Firebase App Distribution, signed release, pilot testing, bump app version, test app update."
argument-hint: "Version, build number, and release notes, for example: 1.1.1 3 Fix login restore"
user-invocable: true
---

# Release Vitalis Mobile

Use the repository release tooling as the SSOT. Do not reproduce its build,
signing, or Firebase commands manually unless diagnosing a failure.

## Fixed Release Configuration

- Android package: `com.vitalis.vitalis`
- Firebase project: `vitalis-ee758`
- Firebase Android app: `1:667160635189:android:cde5b92ba89292ef12ce7c`
- Tester group: `vitalis-users`
- Build root: `Q:\vitalis-firebase-release` on Windows
- Signing secrets: `data/.secrets/mobile-signing/`
- Firebase credentials: `data/.secrets/fcm-service-account.json`
- Expected release certificate SHA-256:
  `F9:23:89:97:B5:CA:96:FD:F2:C8:8E:0F:74:60:85:05:1E:B1:11:9C:40:5E:6F:EE:A2:CE:AC:CC:C1:E6:03:1A`

Never commit, print, paste, or upload signing passwords, keystores, service-account
JSON, access tokens, or expiring binary download URLs.

## Preconditions

1. Read the current versions of `scripts/release_mobile.py`,
   `scripts/release_mobile.ps1`, and `tests/test_release_mobile.py` before
   changing or running the workflow.
2. Confirm the working tree status. Do not include unrelated user changes in a
   release commit.
3. Choose a plain SemVer release name and a build number greater than every
   previously distributed build. Never reuse a build number.
4. Confirm these private files exist and remain ignored:
   - `data/.secrets/mobile-signing/key.properties`
   - `data/.secrets/mobile-signing/upload-keystore.jks`
   - `data/.secrets/fcm-service-account.json`
5. Prefer Node 22 or 24 LTS for Firebase CLI. Node 25 may emit a libuv assertion
   after a successful command.

## Release Procedure

### 1. Validate the Release Tool

Run from the repository root:

```powershell
python -m pytest tests/test_release_mobile.py -q
```

Resolve failures before building. The release script runs the full Flutter test
suite by default; do not pass `-SkipTests` for a normal release.

### 2. Build Without Upload for a New or Risky Change

Use a dry release first when signing, dependencies, native Android code, or the
release tool changed:

```powershell
.\scripts\release_mobile.ps1 `
  -Version 1.1.1 `
  -BuildNumber 3 `
  -Notes "Describe the tester-visible changes" `
  -SkipUpload
```

The tool must:

- run Flutter tests;
- copy source outside OneDrive;
- keep Pub and Gradle caches on the Q: build drive;
- verify critical Android files are present;
- build a release APK with the stable private key;
- verify the APK with `apksigner`;
- print the final SHA-256;
- copy the APK and release notes to `Downloads`.

Do not trust a build made inside the OneDrive workspace.

### 3. Verify the Artifact

Before upload, confirm:

- package is `com.vitalis.vitalis`;
- `versionName` and `versionCode` equal the requested values;
- APK Signature Scheme v2 verifies;
- signer certificate SHA-256 equals the expected fingerprint above;
- the APK exists under `Downloads` and has a recorded SHA-256.

Stop if any identity, version, or signer value differs.

### 4. Publish to Firebase

For the final release, run the same command without `-SkipUpload`:

```powershell
.\scripts\release_mobile.ps1 `
  -Version 1.1.1 `
  -BuildNumber 3 `
  -Notes "Describe the tester-visible changes"
```

The script isolates Firebase CLI configuration and authenticates with the
service account. It must not depend on a cached personal Firebase login.
Confirm Firebase reports all three operations as successful:

- binary uploaded;
- release notes added;
- distributed to `vitalis-users`.

Share the stable Firebase tester release page, not the one-hour binary URL.

## Tester Verification

For the first stable-signed build on a device:

1. Accept the Firebase App Distribution invitation using the invited Google
   account.
2. Install `1.1.0 (2)` from Firebase App Tester or the tester release page.
3. If Android reports a signing conflict with an older manually distributed
   build, uninstall Vitalis once and install the Firebase build. Cloud data is
   retained, but local tokens and caches are cleared.
4. Sign in with the same Microsoft Entra account to restore the same cloud user.
5. Verify dashboard, meals, goals, reports, biometrics, and push registration.
6. Grant Health Connect permissions again if Android asks after reinstall.

To prove future updates work, distribute a higher build such as `1.1.1 (3)` and
install it over `1.1.0 (2)` without uninstalling. Verify the app updates in
place and cloud data remains available.

## Failure Rules

- Missing signing or Firebase files: stop; never fall back to debug signing.
- OneDrive build path: move the build to Q: before retrying.
- Kotlin `different roots`: ensure both `PUB_CACHE` and `GRADLE_USER_HOME` are
  under the Q: build root.
- Missing or empty `MainActivity.kt`: stop; do not ship even if Gradle succeeds.
- Firebase `403`: verify the service account still has
  `roles/firebaseappdistro.admin` on `vitalis-ee758`.
- Firebase group `404`: App Distribution/group initialization is missing; use
  an authorized owner once to create `vitalis-users`, then return to service
  account automation.
- Never bypass failed tests, signature verification, or package/version checks
  to complete a release.

## Commit Discipline

When release tooling changes, stage only the intended files, run a staged diff
secret scan, and keep all files under `data/.secrets/` out of Git. Use a
conventional commit such as `feat: update mobile release workflow`.
