---
mode: agent
description: |
  Prepare a VS Code extension for publishing to a Market+ private marketplace feed.
  Use this prompt ONLY when the user asks to publish, prepare, or set up an extension for Market+,
  AND the workspace contains a VS Code extension (package.json with "engines.vscode").
  Do NOT use this prompt for non-extension projects or unrelated tasks.
tools:
  - read_file
  - replace_string_in_file
  - run_in_terminal
  - create_file
---

# Prepare Extension for Market+

**When to use:** The user wants to publish their VS Code extension to a **Market+** private marketplace feed (backed by Azure DevOps Universal Packages). Only proceed if the workspace has a `package.json` with `"engines": { "vscode": "..." }`.

## Steps

### 1. Add the `marketPlus` field to package.json

Open the workspace's `package.json` and add a top-level `marketPlus` field:

```json
"marketPlus": {
  "packageName": "<package-name>",
  "feed": "<feed-name>",
  "organization": "https://dev.azure.com/<org>/"
}
```

- `packageName`: Use the extension's `"name"` field. Must be lowercase, no spaces, hyphens allowed.
- `feed`: The Azure DevOps Universal Packages feed name. Ask the user if unknown.
- `organization`: The ADO organization URL. Ask the user if unknown.

If the field already exists (`marketPlus` or legacy `adoExtensionFeed`), skip this step.

### 2. Verify required package.json fields

Ensure these exist:
- `"name"` — lowercase, no spaces
- `"displayName"` — human-readable name
- `"description"` — brief description
- `"version"` — semver (e.g., `"1.0.0"`)
- `"publisher"` — publisher ID
- `"engines"` — must include `"vscode"` constraint
- `"main"` — entry point (e.g., `"./dist/extension.js"`)

If any are missing, ask the user or suggest defaults.

### 3. Package as .vsix

```bash
# Build if needed:
npm run build

# Package:
npx vsce package --no-dependencies --allow-missing-repository
```

### 4. Publish to the ADO feed

```bash
az artifacts universal publish \
  --organization <organization> \
  --feed <feed> \
  --name <packageName> \
  --version <version> \
  --path <path-to-vsix> \
  --description "<displayName>"
```

### Prerequisites
- `az` CLI with the `azure-devops` extension
- Authenticated via `az login` or `AZURE_DEVOPS_EXT_PAT`
- `npx vsce` available (`npm install -g @vscode/vsce` if needed)

## Notes

- The `marketPlus` field is ignored by vsce and the VS Code Marketplace — safe to add.
- Always increment the version before publishing a new release.
- Legacy field name `adoExtensionFeed` is also supported but prefer `marketPlus`.
