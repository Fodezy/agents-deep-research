# Slice X: **Structured-Agents Overhaul** – Updated Plan

*(Tool Execution Pipeline Fixed + 4-Model Architecture + Outlines + Structured Summarization)*

---

## 1  Executive Summary & Core Objective

**BREAKTHROUGH**: Tool execution pipeline issue **RESOLVED** through 4-model architecture approach. Local models like `hermes3:8b` don't support function calling, but dedicated `TOOL_CALLING_MODEL` (`Salesforce_Llama-xLAM-2-8b-fc-r-GGUF`) produces proper structured function calls.

**Validated Success Path:**
```
TOOL_CALLING_MODEL → ResponseFunctionToolCall → functions count: 1 → Tool Executed ✅
hermes3:8b → ResponseOutputMessage → functions count: 0 → No Tools ❌
```

This slice now focuses on completing the structured-agents architecture:

* **4-Model Role Separation** (PLANNER, TOOL_CALLING, SUMMARISER, WRITER) - **PRIORITY 1**
* **Structured Summarization** via Outlines (currently returns prose, needs JSON)
* **ValidationWrapper** for auto-repair and observability
* **Model-Role Registry** enforcement with runtime assertions

**Business value:** 98%+ valid outputs, zero `OutputParserError`, functional tool execution, and reliable 4-model local architecture.

Success KPIs (launch +30 days):

| Metric                         | Target  |
| ------------------------------ | ------- |
| Structural-validity rate       | ≥ 98 %  |
| Avg. extra latency             | ≤ +20 % |
| Summarisation F-score vs. gold | ≥ 0.85  |
| OutputParserError incidents    | 0       |

---

## 2  Key Questions, Risks, and Assumptions

### 2.1  Key Questions (Discovery)

| # | Domain     | Question                                                                                 |
| - | ---------- | ---------------------------------------------------------------------------------------- |
| 1 | Product/UX | Do researchers need visibility into auto-repair attempts?                                |
| 2 | Product/UX | Should summariser expose chunk-level debug artifacts?                                    |
| 3 | Technical  | Will all chosen local models respect Outlines function specs?                            |
| 4 | Technical  | What’s the latency impact of two-stage summarisation on crawl bursts?                    |
| 5 | Technical  | Can ValidationWrapper be fully asynchronous without dead-locking current ResearchRunner? |
| 6 | Business   | Which KPI is most critical for initial marketing (error-free or cost-savings)?           |

### 2.2  Potential Risks

| # | Type      | Risk                                                        | Mitigation                                             |
| - | --------- | ----------------------------------------------------------- | ------------------------------------------------------ |
| 1 | Technical | Local model ignores function schema → still spits prose     | Fallback to few-shot “JSON-only” guard; measure & flag |
| 2 | Technical | Validation retry adds >100 % latency on worst pages         | Cap retries = 1, collect metrics, optimise later       |
| 3 | Technical | Hierarchical Summariser blows context window for slow model | Limit chunk summaries to 120 tokens, truncate tails    |
| 4 | Product   | Researchers confused by model-role matrix configuration     | Provide docs + CLI `--models list` helper              |
| 5 | Ops       | New dependencies (Outlines) break Docker build              | Pin versions, add smoke CI                             |

### 2.3  Core Assumptions

* Malformed JSON, not logical mistakes, cause > 90 % of current failures.
* Outlines’ streaming JSON generation works with Llama-3, Phi-3, Mistral, Qwen.
* Single retry is enough to fix most formatting errors.
* Researchers value reliability over raw latency increase.

---

## 3  Proposed MVP

### 3.1  Core Functionality

1. **Outlines integration** for three agents: Planner, ToolSelector, KnowledgeGap.
2. **ValidationWrapper** with Pydantic schema validation, one auto-repair retry, and metrics hooks.
3. **HierarchicalSummariser** pipeline inside WebSearchAgent & SiteCrawlerAgent (token-based chunker → fast summariser → slow aggregator).
4. **Model-Role Registry** in `llm_config.py` with HF tags (`text-generation`, `summarization`).
5. **Observability**: counters `validation_failed`, `repair_success`, `repair_failed`, latency timers.

### 3.2  Out of Scope (for MVP)

* Full conversion of WriterAgent to Outlines (guardrails only).
* Advanced retry strategies (chain-of-thought self-correct).
* UI/UX surfaces for debug artefacts.
* Distributed crawl throttling.

---

## 4  Phased Implementation Plan

| Phase                                        | Sprint(s) | Deliverables                                                                                                                              |
| -------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — Model-Role Registry (PRIORITY)**      | 0.5       | 4-model role enforcement (PLANNER/TOOL_CALLING/SUMMARISER/WRITER); runtime assertions; config validation                                |
| **2 — Outlines Core Agents**                | 1         | ToolSelector, Planner, KnowledgeGap migrated to Outlines; structured function schemas                                                    |
| **3 — Structured Summarization**            | 1         | Summariser produces JSON not prose; Outlines-based `summarize_content` function; schema validation                                       |
| **4 — ValidationWrapper & Observability**   | 1         | Auto-repair wrapper for all structured outputs; metrics hooks; retry logic                                                               |
| **5 — QA & Regression Protection**          | 1         | Both clean (structured calls) and degraded (fallback) path tests; benchmark suite; migration docs                                       |

*Total ≈ 4.5 sprints (5 calendar weeks).*

---

## 5  Initial Backlog (Ticket-Ready Stories)

### Epic — Structured-Agents Overhaul *(Updated Priorities)*

**HIGH PRIORITY (Do Now)**

| ID            | Title                                      | Type  | Description                                                    | AC (summary)                                     | Depends |
| ------------- | ------------------------------------------ | ----- | -------------------------------------------------------------- | ------------------------------------------------ | ------- |
| **HYBRID-08** | Model-Role Registry & Tag Checker         | Story | Codify 4-model roles (PLANNER/TOOL_CALLING/SUMMARISER/WRITER) | Runtime assertions pass; config validates roles | —       |
| **HYBRID-05** | Outlines refactor — ToolSelector           | Story | Already in progress; structured tool selection JSON           | 98% valid JSON; no function call parse errors   | —       |
| **HYBRID-06** | Outlines refactor — Planner                | Story | Structured planning output via Outlines                       | Plan JSON passes schema validation               | 05      |
| **HYBRID-04a**| Outlines-based Summariser (structured output) | Story | **NEW**: Summariser must emit JSON not prose using Outlines   | Structured summary with sources array           | 08      |

**SECONDARY PRIORITY**

| ID            | Title                              | Type  | Description                                                  | AC (summary)                              | Depends     |
| ------------- | ---------------------------------- | ----- | ------------------------------------------------------------ | ----------------------------------------- | ----------- |
| **HYBRID-07** | Outlines refactor — KnowledgeGap   | Story | `report_gaps` function with structured output                | Gap JSON valid; retry <2%                | 06          |
| **HYBRID-02** | ValidationWrapper + Observability  | Story | **UPDATED**: Wrap Outlines outputs with validation/repair   | Auto-repair 80%+ malformed cases         | 04a,05,06   |
| **HYBRID-09** | WriterAgent guardrails             | Story | Final output polishing and length enforcement                | Writer passes quality tests              | 06          |
| **HYBRID-10** | E2E benchmark & docs               | Story | Regression tests for both clean + degraded function paths   | All KPIs met; migration guide published  | 07,08,09    |

**COMPLETED/IN-FLIGHT** *(Reference Only)*
- HYBRID-01: Schema definitions (completed)
- HYBRID-03: Token chunker (completed) 
- HYBRID-04: Hierarchical summarizer base (completed)

---

## 6  Definition of Done (DoD)

**UPDATED Success Criteria:**

* **4-Model Architecture**: TOOL_CALLING_MODEL produces structured function calls (not plaintext)
* **Function Call Pipeline**: `ResponseFunctionToolCall` → `functions count: 1` → Tools execute successfully  
* **Structured Summarization**: Summariser emits JSON with `{output, sources}` structure (not prose)
* **Outlines Integration**: Core agents (ToolSelector, Planner, KnowledgeGap) use Outlines functions
* **ValidationWrapper**: Auto-repairs ≥ 80% of malformed cases; zero `OutputParserError` on regression
* **Regression Coverage**: Tests for both clean (structured) and degraded (fallback) function call paths
* **End-to-End Validation**: "Quantum entanglement" query completes with tool execution + structured output
* **KPI Targets**: Hit metrics from Section 1
* **Documentation**: Migration guide includes 4-model setup and troubleshooting

---

### 📌 Next Action

**IMMEDIATE**: Kick-off **HYBRID-08** (Model-Role Registry) to formalize the 4-model architecture that was validated in testing. This becomes the foundation for all subsequent structured agent work.

**DESIGN DECISIONS NEEDED**:
1. Summariser schema: Simple `{summary, sources}` or rich `{output, key_findings, confidence, sources}`?
2. Model assignment: Which model handles summarization in 4-model split?
3. ValidationWrapper: Before or after downstream agents receive summariser output?
