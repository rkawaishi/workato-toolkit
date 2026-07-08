
# Reference: genie

Generate the full file set for a Workato Genie (AI agent).
Covers the Genie itself and its skills. For MCP exposure (alone or in addition), also apply [references/mcp-server.md](mcp-server.md).

## Genie vs MCP Server — when to use which

| | Genie | MCP Server |
|---|---|---|
| **Purpose** | Conversational AI agent | Expose tools to external AIs |
| **Channels** | Slack, Teams, Workato GO | Claude Desktop, Cursor, ChatGPT |
| **Files** | `.agentic_genie.json` | `.mcp_server.json` |
| **Skill references** | Direct via `references` | Ordered + described via the `tools[]` array |
| **AI instructions** | `instructions` (system prompt) | `tools[].description` (tool-selection guidance) |

- **Genie only**: a conversational agent for internal chat.
- **MCP Server only**: tools callable from external AI editors / chat.
- **Both**: usable inside Genie and callable externally (skills/recipes can be shared).

## Procedure

1. Interview the user:
   - **Genie purpose**: what AI agent are we building?
   - **Target users**: who uses it?
   - **Skill list**: which skills should the Genie have (purposes of each)?
   - **AI provider**: `anthropic` / `openai` (default: `anthropic`).
   - **Target project**: which project directory to create in.
   - **MCP exposure**: also expose as an MCP server? (default: No.)
   - **VUA**: is Verified User Access needed (API calls using the end user's credentials)?

2. Read the references (fetch each format spec via `workato_asset_path(...)`, then Read the returned path — always-on rules in the main session, but the builder subagent has none):
   - `workato_asset_path("rules/workato-agentic-format.md")`
   - `workato_asset_path("rules/workato-recipe-format.md")`
   - `workato_asset_path("rules/workato-project-structure.md")`
   - Call `workato_docs_lookup` with path `connectors/_index.md`, then look up each relevant connector with `workato_docs_lookup` (path `connectors/<connector>.md`)
   - Call `workato_docs_lookup` with path `platform/agent-studio.md`
   - Call `workato_docs_lookup` with path `platform/mcp.md`

3. If an existing Genie is available, reference its structure.

4. Generate the Genie configuration files (following the project-structure spec fetched in step 2):
   - `<project>/Agents/<name>.agentic_genie.json` — the Genie itself.
   - For each skill:
     - `<project>/Agents/<skill_name>.agentic_skill.json` — skill definition.
   - For MCP exposure: `<project>/Agents/<name>.mcp_server.json` — MCP server definition.
   - Make sure `zip_name` / `folder` inside the JSON include the subfolder path.

   > **Dispatch the generation.** Hand this file generation to the **`workato-builder` subagent** (asset type `genie`; bundled with the plugin — invoke it via Claude Code's subagent mechanism). Pass the design from steps 1–3, the `instructions` / skill-recipe / MCP-server conventions in the sections below, and the target paths. The subagent writes the files and returns a short summary, keeping the JSON out of the main context. (Only if subagent dispatch is unavailable, generate inline.)

5. **Create the skill recipes by applying [references/recipe.md](recipe.md)** (same pipeline, recursed per recipe):
   - Lay out each skill's recipe requirements (trigger: `workato_genie/start_workflow`, parameters, external integration targets).
   - The recipe reference handles the Genie-skill-recipe specifics (`as` is random hex, `parameters_schema_json`, etc. — see "Rules for generating a skill recipe" below).

## Generating the Genie's `instructions`

Generate the prompt using this section structure:

```markdown
You are a [Role] Agent

**What's my job?**
[Description of the primary responsibilities]

**Who will need my help?**
[List of target users]

**How do I get things done?**
[List of behavior patterns]

**What should I avoid?**
[List of prohibitions]

**What results do you want me to track?**
[Metrics to follow]

**How should I talk to people?**
[Communication style]

**Any extra tips?**
[Anything else]
```

## Rules for generating a skill recipe

- Trigger: `workato_genie` / `start_workflow`.
- Use a random 8-character hex value for `as` (Genie-skill-recipe convention).
- `input.parameters_schema_json`: input parameter schema (JSON string).
- `input.result_schema_json`: output schema (JSON string).
- `input.requires_user_confirmation`: `"false"` (default).
- `input.description`: same as the skill's `trigger_description`.
- Parameter reference: `path:["parameters","<param_name>"]` — nested under `parameters`.
- Final step: `workato_genie` / `workflow_return_result` returns the result.
- `workflow_return_result` input: map each field individually as `input.result.<field>`.
  ```json
  "input": {
    "result": {
      "field1": "#{_dp('...')}",
      "field2": "#{_dp('...')}"
    }
  }
  ```
- `extended_output_schema` / `extended_input_schema` expand the `result_schema_json` fields under a `result` object.
- Intermediate steps: the actual business logic (Salesforce lookup, API calls, etc.).

## Calling a Genie from a recipe: `assign_task_to_genie`

Delegate a task to a Genie from inside a recipe:

```json
{
  "provider": "workato_genie",
  "name": "assign_task_to_genie",
  "keyword": "action",
  "dynamicPickListSelection": { "genie_handle": "Genie name" },
  "toggleCfg": { "genie_handle": true },
  "input": {
    "genie_handle": {
      "zip_name": "Agents/genie.agentic_genie.json",
      "name": "Genie name",
      "folder": "Agents"
    },
    "task_instructions": "Task instructions (datapills allowed)"
  }
}
```

- `genie_handle`: references the Genie to invoke (by `zip_name`).
- `task_instructions`: task instructions for the Genie (you can inject context via datapills).
- Use cases: ask a Genie to analyze something during an approval flow, dispatch tasks to a Genie on event triggers, etc.

## Output and deployment guide

After generation, display:
- The list of generated files.
- Architecture diagram:
  - Genie only: `Genie → Skills → Recipes`.
  - With MCP: `Genie → Skills → Recipes ← MCP Server`.
- A summary of each skill's `trigger_description`.
- For MCP: a summary of the MCP server's `tools[]`.

Follow the deployment guide (call `workato_docs_lookup` with path `patterns/deployment-guide.md`) and walk through the deploy:
1. Push connections first → guide UI auth (for new connections).
2. Push every other asset.
3. Guide the user through the field-mapping review of skill recipes in the UI.
4. For MCP: guide server enablement and AI-client configuration.
5. Guide the test run.

