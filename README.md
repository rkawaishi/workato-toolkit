# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a native plugin/extension.
Targets Claude Code, Cursor, Codex CLI (Gemini CLI to follow).

> Status: MVP scaffolding (P1). See the design spec in workato-dev-kit `superpowers/`.

## Install (MVP: CC / Cursor / Codex)

### Claude Code
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

### Codex CLI
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```

### Cursor
Add via the Cursor plugin marketplace, or for local dev reference the repo with `@local`.

After install, run the `ping` skill to verify the toolkit is loaded.

## License
MIT
