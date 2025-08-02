# Slice X: **Structured-Agents Overhaul** – Kick-off Plan

*(Outlines + JSON Validation/Auto-Repair + Hierarchical Summarisation + Model-Role Registry)*

---

## 1  Executive Summary & Core Objective

The current **agents-deep-research** pipeline frequently crashes on malformed JSON, chokes on long webpages, and makes model swaps painful.
This slice will ship a *structured-agents overhaul* that introduces:

* **Outlines** for native function-style JSON generation.
* A **ValidationWrapper** with single-retry auto-repair and observability.
* A **Hierarchical Summariser** (chunk → fast model → slow model) embedded in search/crawl agents.
* A **Model-Role Registry** with Hugging Face tags for clear benchmarking.

**Business value:** 98 %+ valid outputs, zero `OutputParserError` in regression suite, and the ability to ingest 25 k-token pages—unlocking reliable, low-cost research on local models.

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

| Phase                                      | Sprint(s) | Deliverables                                                                                                                            |
| ------------------------------------------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — Foundations**                        | 1         | Outlines lib installed; base function schemas (`create_plan`, `select_tools`, `report_gaps`); ValidationWrapper skeleton; metrics hooks |
| **2 — Search & Crawl Refactor**            | 1         | Token chunker util; fast-summariser loop; slow-model aggregator; integrated into WebSearch & Crawl agents                               |
| **3 — Core Agent Conversion**              | 1         | PlannerAgent, ToolSelectorAgent, KnowledgeGapAgent migrated to Outlines; legacy regex removed                                           |
| **4 — Model Registry & Writer Guardrails** | 0.5       | Registry w/ tags, CLI switch; WriterAgent length/markdown guard                                                                         |
| **5 — QA & Roll-out**                      | 1         | Regression suite (quantum query); latency benchmark; docs & migration guide                                                             |

*Total ≈ 4.5 sprints (5 calendar weeks).*

---

## 5  Initial Backlog (Ticket-Ready Stories)

### Epic — Structured-Agents Overhaul

| ID            | Title                              | Type  | Description                                                  | AC (summary)                              | Depends  |
| ------------- | ---------------------------------- | ----- | ------------------------------------------------------------ | ----------------------------------------- | -------- |
| **HYBRID-01** | Failure analysis & schema defs     | Story | Catalogue malformed samples, finalise JSON schemas           | Doc of patterns; `schemas/` v1 JSON files | —        |
| **HYBRID-02** | ValidationWrapper + Observability  | Story | Build async validator, auto-repair, metrics                  | Pass unit suite; emits counters           | 01       |
| **HYBRID-03** | Token chunker util                 | Story | Implement `split_on_tokens` (≈800) with offset map           | 100 % cov; handles >25 k tokens           | 02       |
| **HYBRID-04** | HierarchicalSummariser integration | Story | Fast model per-chunk, slow aggregation, JSON output          | Summarises Wikipedia 30 k tokens <30 s    | 03       |
| **HYBRID-05** | Outlines refactor — ToolSelector   | Story | Replace prompt f-string with `select_tools` function         | 98 % valid JSON in tests                  | 02       |
| **HYBRID-06** | Outlines refactor — Planner        | Story | Implement `create_plan` function; update IterativeResearcher | Plan JSON passes schema                   | 05       |
| **HYBRID-07** | Outlines refactor — KnowledgeGap   | Story | `report_gaps` function + few-shot                            | Gap JSON valid; retry <2 %                | 06       |
| **HYBRID-08** | Model-Role Registry & Tag checker  | Story | YAML registry + assert correct HF tag                        | Fails fast on wrong tag                   | 02       |
| **HYBRID-09** | WriterAgent guardrails             | Story | Enforce max length & strip stray markdown                    | Writer passes proofread tests             | 06       |
| **HYBRID-10** | E2E benchmark & docs               | Story | Run quantum query; latency + error metrics; write guide      | All KPIs met; guide published             | 07,08,09 |

---

## 6  Definition of Done (DoD)

* All JSON-emitting agents generate via Outlines with versioned schemas.
* ValidationWrapper auto-repairs ≥ 80 % of synthetic malformed cases; zero `OutputParserError` on regression suite.
* Search & Crawl agents summarise a 25 k-token page without OOM or timeout.
* End-to-end “quantum entanglement” run completes on local model stack.
* KPI targets hit (Section 1).
* CI includes schema regression tests & latency benchmark.
* Migration guide, troubleshooting, and model-tag matrix documented.

---

### 📌 Next Action

Kick-off **HYBRID-01** (failure analysis & schema definitions) and schedule a design-review meeting at sprint start + 2 days.
