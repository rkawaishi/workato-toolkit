# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a native plugin.
Officially supports **Claude Code**, **Cursor**, and **Codex CLI**. Gemini CLI is coming soon.

The toolkit bundles skills, the Workato knowledge base (300+ connectors, logic, platform, patterns),
always-on rules, a credential-guard hook, and a docs-overlay MCP server — all from one shared tree.
Nothing to vendor into your repo and nothing to symlink.

## Install

### Claude Code
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

### Cursor
```
# Cursor → Settings → Plugins → Add marketplace
#   source: rkawaishi/workato-toolkit
# then install "workato-toolkit"
```

### Codex CLI
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```

### Gemini CLI
Coming soon (pending runtime verification). It will be:
`gemini extensions install rkawaishi/workato-toolkit --ref vX.Y.Z`.

After install, run the `ping` skill to verify the toolkit is loaded.

## Updating

- **Claude Code:** `/plugin update workato-toolkit`
- **Codex CLI:** `codex plugin update workato-toolkit`
- **Cursor:** update from the Plugins panel.

Pin to a release tag where your editor supports it (e.g. Gemini `--ref vX.Y.Z`).

## Security hardening (recommended)

The plugin ships a credential-guard hook that blocks an agent from surfacing secret-file
contents. Because a plugin cannot distribute an editor deny-list, add defense-in-depth to
**your workspace repo**:

### Claude Code — `.claude/settings.json`
```json
{
  "permissions": {
    "deny": [
      "Read(./**/master.key)",
      "Read(./**/settings.yaml)",
      "Read(./**/settings.yaml.enc)",
      "Read(./**/.resource-providers.yml)",
      "Read(./**/.env)",
      "Read(./**/.env.*)",
      "Read(./**/*.key)",
      "Read(./**/*.pem)",
      "Read(./**/*.secret)",
      "Read(./**/*.credential*)"
    ]
  }
}
```

### Codex / Cursor / Gemini — `.codexignore` / `.cursorignore` / `.geminiignore`
Create the matching file at your workspace root:
```gitignore
master.key
settings.yaml
settings.yaml.enc
.resource-providers.yml
.env
.env.*
*.key
*.pem
*.secret
*.credential*
```
> `.workatoenv` is intentionally NOT excluded — it holds only project/folder/workspace IDs (no tokens).

## Documentation

Per-editor quickstarts and architecture live in [`docs/guides/`](docs/guides/). Knowledge-base
docs are served on demand through the docs-overlay MCP (`workato_docs_lookup` / `workato_docs_list`).

## License
MIT
