# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a
native **Claude Code plugin**.

The toolkit bundles skills, the Workato knowledge base (300+ connectors, logic, platform,
patterns), always-on rules, a credential-guard hook, and a docs-overlay MCP server — all
from one shared tree. Nothing to vendor into your repo and nothing to symlink.

> **Editor support:** Claude Code is the only officially supported editor. Cursor /
> Codex CLI / Gemini CLI support is **on hold** — their assets remain in the tree
> (frozen) but are not maintained or verified.

## Install (Claude Code)

```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

After install, run the `ping` skill to verify the toolkit is loaded.

## Updating

```
/plugin update workato-toolkit
```

Pin to a release tag where you need reproducibility.

## Repository layout

| Path | What it is |
|---|---|
| `plugin/` | **The distributed plugin** — skills, knowledge base (`plugin/docs/`), always-on rules (`plugin/rules/`), hook scripts (`plugin/bin/`), the docs-overlay MCP. Everything under it ships to users. |
| `.claude-plugin/marketplace.json` | Marketplace definition (resolved from the repo root; its `source` points at `./plugin`). |
| `scripts/`, `tests/`, `.github/`, `dev/`, `CLAUDE.md` | Development tooling and documents for building the toolkit itself. Not part of the product surface. |
| Frozen editor assets | `plugin/rules/*.mdc`, `plugin/agents/*.toml`, `plugin/GEMINI.md`, the cursor/codex hooks variants and manifests, `.cursor-plugin/`, `.agents/` — kept for a future revival, not maintained. |

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

### Other editors — `.codexignore` / `.cursorignore` / `.geminiignore`
If you nonetheless use a frozen editor, create the matching ignore file at your
workspace root:
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

Guides live in [`plugin/docs/guides/`](plugin/docs/guides/). Knowledge-base docs are
served on demand through the docs-overlay MCP (`workato_docs_lookup` / `workato_docs_list`).

## License
MIT
