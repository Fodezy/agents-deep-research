Below is a **high-level migration roadmap** – no line-by-line code, just the steps, files, and responsibilities – for upgrading your current “prompt-only” pipeline to the hybrid (function-schema + auto-repair + few-shot) approach.

---

## 0. Guiding Principles

| Pillar                               | What It Means for You                                                                                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Native function calling**          | Every agent that needs to return structured data (Planner, ToolSelector, SiteCrawler, WebSearch, etc.) is exposed to the model as an OpenAI “function” with a JSON Schema.           |
| **Wrapper validation & auto-repair** | Every time the model responds, you validate its `arguments` against the matching Pydantic model. If invalid, re-prompt once or twice with a terse “fix-it” message before giving up. |
| **Few-shot**                         | Keep a tiny set of gold-standard function-call examples in the prompt history for each agent. Only 1-3 short examples are usually enough.                                            |

---

## 1. Where to Touch the Code (Top-Level View)

| Layer                   | Files / Modules                                                                                                              | What you’ll add / change                                                                                                                               |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Schemas & Functions** | `agents/tool_selector_agent.py`, `planner_agent.py`, `knowledge_gap_agent.py`, plus each tool agent in `agents/tool_agents/` | Replace giant `INSTRUCTIONS` strings with *system* messages + JSON-Schema function specs.                                                              |
| **LLM wrapper**         | `agents/baseclass.py` **or** a new small helper in `utils/`                                                                  | • Call the model with `functions=[…schema…]`.<br>• Validate `arguments` with Pydantic.<br>• If validation fails: re-prompt the model once, then raise. |
| **Few-shot store**      | Could be inline in each agent file or a small YAML/JSON in `agents/utils/examples/`                                          | A couple of canonical Q → function-call examples per agent.                                                                                            |
| **Config plumbing**     | `llm_config.py`                                                                                                              | Add helpers for passing the `functions` list and system prompt to the underlying chat-completion call.                                                 |

---

## 2. Implementation Steps (Phase-by-Phase)

### Phase A  — Add Function Schemas

1. **Pick one agent first** (e.g., *ToolSelector*).
2. Define its schema as a Python dict (or Pydantic `model_json_schema()` dump).
3. Pass that schema in the `functions` parameter when you call OpenAI.
4. Remove the JSON template from its instruction string; keep only a short system prompt like:

   > “You are the ToolSelector. Return a `select_tools` function call.”

Verify that the model now returns something like:

```json
{
  "name": "select_tools",
  "arguments": {
    "tasks": [ … ]
  }
}
```

### Phase B  — Central Validation + Auto-Reprompt

1. In `agents/baseclass.py` (or a new helper), wrap `ResearchRunner.run()` so that after the chat call you:

   * Parse `response.choices[0].message.function_call.arguments`.
   * `pydantic_model.parse_obj(… )`
   * On `ValidationError`, issue a *single* follow-up prompt:
     *“The JSON you returned was invalid because X. Please reply with only a corrected function call.”*
   * If it still fails, raise your existing `OutputParserError`.

### Phase C  — Few-Shot Examples

1. For stubborn agents (e.g., SiteCrawlerAgent), prepend 1–2 *assistant* messages **before** the user call that show a valid function call.
2. Keep each example < 25 tokens; no prose.

### Phase D  — Iterate Agent-by-Agent

Repeat Phases A–C for:

* `planner_agent` → returns `create_plan` function
* `knowledge_gap_agent` → returns `report_gaps` function
* `tool_agents/*` → each returns its own specific function or summary object

Deploy incrementally; run unit tests after each agent conversion.

---

## 3. Testing & Roll-out

1. **Unit tests**: Add pytest cases that mock the chat response with both *valid* and *broken* JSON to ensure your auto-repair logic works.
2. **Dry run**: `python -m deep_researcher.main --mode deep --query "smoke test"` and confirm:

   * No `OutputParserError`s from JSON shape issues.
   * No markdown fences/backticks in returned arguments.
---

## 4. Long-Term Maintenance Tips

* **Version your schemas** so future field additions don’t break older code.
* Keep **few-shot examples** tiny; update them when you change schema.
* Add a **metrics counter**: “auto-repair attempts per call.” Spikes mean your prompt drifted.

---

### Bottom Line

By shifting the shape-enforcement burden from giant f-strings to OpenAI function calls + programmatic validation, you’ll virtually eliminate the stream of parse errors you’re seeing now. The wrapper’s auto-repair closes the remaining gap, and few-shot keeps the model anchored. This roadmap gives you the high-level moves—you can now schedule concrete coding tasks file-by-file.
