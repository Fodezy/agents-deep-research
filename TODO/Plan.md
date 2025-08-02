# 🌐 Agents-Deep-Research 2.0 — **Master Implementation Plan**

*(Outlines + JSON-Validation/Auto-Repair + Hierarchical Summarisation + Model-Role Tagging)*

---

## 0  Executive Snapshot

| Pain-Point                           | Solution Pillar                                                    | Benefit                                  |
| ------------------------------------ | ------------------------------------------------------------------ | ---------------------------------------- |
| Malformed JSON → `OutputParserError` | **Outlines structured generation + ValidationWrapper auto-repair** | 98 %+ valid outputs, 1-retry max         |
| Context overflow on large pages      | **Hierarchical chunk-summarisation**                               | Handles 30 k tokens pages; lower cost    |
| Model confusion / swap friction      | **Model-Role registry with hub tags**                              | Clear mapping; easy benchmarking & swaps |

---

## 1  New Canonical Architecture

```
User Query
   │
   ▼
Planner Agent (PLANNER_MODEL 🧠 — Tag: Text Generation)
   ├─ Outlines→ create_plan()
   ▼
Iterative Loop per Section
   ├─ KnowledgeGapAgent   (Text Gen)
   ├─ ToolSelectorAgent ⚙ (TOOL_CALLING_MODEL — Tag: Text Generation)
   │     • Outlines→ select_tools()
   │
   ├─ WebSearch / Crawl Agents
   │     • scrape → Chunker → SUMMARIZATION_MODEL 📝 (Tag: Summarization)
   │     • chunk summaries → slow model aggregation (WRITER_MODEL ✍️ or same Summariser)
   │
   └─ WriterAgent  ✍️ (Tag: Text Generation)
Final Proofread → Report
```

*Every agent that outputs JSON is now an **Outlines function**; every free-text generation is guarded by ValidationWrapper.*

---

## 2  Pillar 1 — Outlines-Based Structured Generation

| Step                                                                                                           | Action |
| -------------------------------------------------------------------------------------------------------------- | ------ |
| **A.** Add `outlines` to project dependencies                                                                  |        |
| **B.** Define function schemas in pure JSON (versioned) — e.g. `select_tools`, `knowledge_gaps`, `create_plan` |        |
| **C.** Refactor agents to call `outlines.generate(function=…, prompt=…)` instead of f-string coercion          |        |
| **D.** Remove regex “fixers” from `parse_output.py`                                                            |        |

---

## 3  Pillar 2 — ValidationWrapper + Auto-Repair

1. **Intercept** every LLM response.
2. **If** Outlines returns text → extract `function_call.arguments`.
3. **Pydantic validate** vs schema.
4. **On error** → single repair prompt:

   ```
   Your JSON failed because: {error}. 
   Return ONLY corrected JSON for {function_name}.
   ```
5. Metrics emitted: `validation_failed`, `repair_success`, `repair_failed`, latency.

*Library location*: `deep_researcher/agents/utils/validation_wrapper.py`.

---

## 4  Pillar 3 — Hierarchical Summarisation Engine

| Phase           | Algorithm                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------ |
| **Chunking**    | `strip_html→split_on_tokens(≈800)`                                                               |
| **Per-chunk**   | call fast `SUMMARIZATION_MODEL` (e.g. φ-mini) → bulleted summary                                 |
| **Aggregation** | concatenate chunk summaries → large-context model (Qwen-30B or Writer) produces polished summary |
| **Output**      | JSON `{ "points": [...] }` ready for WriterAgent                                                 |

*Lives inside `tools/web_search.py` & `tools/crawl_website.py`.*

---

## 5  Model-Role Registry & Tags

```yaml
models:
  planner:             meta-llama-3-8b-instruct   # tag: text-generation
  tool_caller:         phi3-mini-128k            # tag: text-generation
  summariser_fast:     mistral-7b-instruct        # tag: summarization
  summariser_slow:     qwen-30b-chat              # tag: text-generation
  writer:              qwen-30b-chat              # tag: text-generation
```

*Registry lives in `llm_config.py`; utility enforces that chosen model advertises the correct hub tag.*

---

## 6  Phased Delivery Timeline

| Phase                          | Duration | Key Deliverables                                                           |
| ------------------------------ | -------- | -------------------------------------------------------------------------- |
| **0. Kick-off**                | 0.5 wk   | Sign-off on plan, pick models                                              |
| **1. Foundations**             | 1 wk     | Outlines installed, ValidationWrapper + metrics                            |
| **2. Search & Crawl Refactor** | 1 wk     | Chunker + HierarchicalSummariser integrated; agents emit JSON via Outlines |
| **3. Core Agents Conversion**  | 1 wk     | Planner, ToolSelector, KnowledgeGap → Outlines                             |
| **4. Writer/Tuning**           | 0.5 wk   | Writer guardrails, final proofread pass                                    |
| **5. QA & Roll-out**           | 1 wk     | E2E tests, latency bench, feature flags, docs                              |

*Total: ≈ 5 weeks.*

---

## 7  Ticket-Ready Backlog (excerpt)

| ID            | Story                                                | Depends On |
| ------------- | ---------------------------------------------------- | ---------- |
| **HYBRID-01** | Failure analysis & schema definitions                | —          |
| **HYBRID-02** | ValidationWrapper + Observability                    | 01         |
| **HYBRID-03** | Model Registry + Tag checker                         | 02         |
| **HYBRID-04** | Implement Chunker util                               | 02         |
| **HYBRID-05** | Integrate HierarchicalSummariser into WebSearchAgent | 04         |
| **HYBRID-06** | Outlines refactor: ToolSelector                      | 02         |
| **HYBRID-07** | Outlines refactor: Planner                           | 06         |
| **HYBRID-08** | Outlines refactor: KnowledgeGapAgent                 | 07         |
| **HYBRID-09** | WriterAgent length & markdown guard                  | 07         |
| **HYBRID-10** | End-to-End benchmark & doc                           | 08 + 09    |

---

## 8  Quality & Success Metrics

* **Structural Validity Rate** ≥ 98 % (post-retry).
* **Avg Extra Latency** ≤ +20 %.
* **Summarisation F-score** ≥ 0.85 vs gold.
* Zero `OutputParserError` on regression suite.

---

## 9  Definition of Done

* All JSON-emitting agents run on Outlines functions with versioned schemas.
* ValidationWrapper passes unit suite; auto-repair succeeds on ≥ 80 % of synthetic malformed cases.
* WebSearch & Crawl agents summarise 25 k-token Wikipedia page without crash.
* `deep_researcher.main` completes the “quantum entanglement” query end-to-end on local models without manual intervention.
* CI pipeline includes schema regression tests and latency benchmarks.
* Docs: migration guide + troubleshooting + model-tag matrix.

---

### 📌 Next Action

Start **HYBRID-01**: finalise schemas (`select_tools`, `knowledge_gaps`, `create_plan`, `chunk_summary`), choose fast & slow summariser models, and stub the ValidationWrapper.
