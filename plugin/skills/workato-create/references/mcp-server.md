# Reference: mcp-server

Expose Workato skills as an MCP server callable from external AI clients
(Claude Desktop, Cursor, ChatGPT). Builds on the same skill/recipe machinery
as a Genie: `MCP Server → Skills → Recipes` (a Genie is optional — see
[references/genie.md](genie.md) for the decision table and skill-recipe rules).

Consult `workato_docs_lookup("platform/mcp.md")` for the platform behavior.

## Building without a Genie

1. Create the skill recipes (`workato_genie/start_workflow` trigger) by
   applying [references/recipe.md](recipe.md).
2. Generate the skill definitions (`.agentic_skill.json`) per
   [references/genie.md](genie.md)'s skill rules.
3. Generate the MCP server definition (below). No `.agentic_genie.json` needed.

Generation is dispatched to the `workato-builder` subagent per the router's
pipeline step 5 — asset type `genie` (the builder's genie lane covers
`.mcp_server.json`).

## Generating the MCP server file

For MCP exposure, generate `<project>/Agents/<name>.mcp_server.json`:

```json
{
  "name": "Server name",
  "description": "MCP server description (the AI uses this to choose a server)",
  "auth_type": "workato_idp",
  "tools_type": "project_assets",
  "tools": [
    {
      "tool": "ref_0",
      "description": "Use this tool when... / Do not use this tool when...",
      "vua_required": true
    }
  ],
  "references": {
    "ref_0": {
      "type": "agentic_skill",
      "id": {
        "zip_name": "Agents/skill_name.agentic_skill.json",
        "name": "skill_name",
        "folder": "Agents"
      }
    }
  }
}
```

### Guidelines for MCP tool `description`

- This is the instruction the AI uses to pick a tool. Make it more detailed than a Genie's `trigger_description`.
- Prefer "Use this tool when..." / "Do not use this tool when..." phrasing.
- Make the distinction between tools unambiguous.

### Caveats around skill names

When you attach a skill to an MCP server, Workato may rename the skill's `zip_name` to match the recipe name. Keep the skill's file name in lockstep with the recipe name.

### MCP server deployment caveats

- **First push**: the MCP server, skills, and skill recipes are created together.
- **`PG::UniqueViolation` on update**: re-pushing while the skill already exists triggers this error. `agentic_skill` and `mcp_server` cannot be removed via the CLI's `--delete` (they show up as `Skipped`). **Ask the user to delete them manually in the UI**, then re-push.
- **`extended_output_schema` on skill recipes**: actions like `add_record` need `extended_output_schema`; without it, downstream steps can't see the datapills and the recipe fails to start. Set it on every action.

### MCP only (no Genie)

When building only an MCP server without a Genie:
1. Generate the skill recipe (`workato_genie/start_workflow` trigger).
2. Generate the skill definition (`.agentic_skill.json`).
3. Generate the MCP server definition (`.mcp_server.json`).
4. No Genie file (`.agentic_genie.json`) needed.

```
MCP Server → Skills → Recipes (no Genie)
```

