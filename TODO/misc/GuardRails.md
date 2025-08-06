## 🚧 Guard-Rails to Keep HYBRID Slice on Track

*(Prevent scope-creep, hit the 5-week ship date)*

| Area                      | Guard-Rail                                                                           | “If/Then” Rule                                                                                         |                                    |
| ------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| **1. Scope**              | **One ticket = one behavioural change**—no drive-by refactors.                       | *If* you discover unrelated cleanup, *then* open a follow-up ticket; do **not** expand the current PR. |                                    |
| **2. Definition of Done** | Use the **DoD checklist** at PR description; every ticket inherits slice-level KPIs. | *If* any box is unchecked, PR can’t merge.                                                             |                                    |
| **3. Time-boxing**        | 🔒 **2-day cap** on stories, **3-day cap** on spikes.                                | *If* a task overruns, escalate in daily stand-up and split / re-estimate.                              |                                    |
| **4. MVP Focus**          | Anything not in “Core Functionality” is *explicitly* out-of-scope.                   | *If* a stakeholder requests extras, park it in the backlog under “Post-MVP”.                           |                                    |
| **5. Review Policy**      | Require **1 PM + 1 Eng** approval; reviewers enforce schema & tests.                 | *If* code adds a new dependency, add it to `requirements.txt` and update Dockerfile in the same PR.    |                                    |
| **6. WIP Limits**         | Team WIP ≤ **3 parallel stories**.                                                   | *If* limit exceeded, finish/review before starting new work.                                           |                                    |
| **7. Testing**            | **Unit >80 %** coverage on new modules, **CI green** before merge.                   | *If* coverage dips, block merge until tests added.                                                     |                                    |
| **8. Metrics Hook**       | Every JSON-emitting agent must increment \`validation\_success                       | failed\` counters.                                                                                     | *If* metrics missing, PR rejected. |
| **9. Release Cadence**    | End-of-phase demo + tagged release branch.                                           | *If* demo criteria not met, phase cannot close.                                                        |                                    |
| **10. Decision Log**      | Use `/docs/decisions/ADR-###.md` for any architecture change.                        | *If* a PR alters public interfaces, an ADR is mandatory.                                               |                                    |

---

### Ticket-Specific Boundaries

| Ticket                                  | Don’t Do                          | Must Do                                                   |
| --------------------------------------- | --------------------------------- | --------------------------------------------------------- |
| **HYBRID-01** – Schemas                 | Implement ValidationWrapper logic | Catalogue errors, publish **static** JSON schemas v1      |
| **HYBRID-02** – ValidationWrapper       | Touch search/crawl agents         | Pydantic validation, single retry, metrics                |
| **HYBRID-03/04** – Chunker + Summariser | Optimise latency                  | Ship functional pipeline; note perf findings              |
| **HYBRID-05-08** – Outlines Refactors   | Re-design prompts                 | Replace with `outlines.generate`; keep original agent API |
| **HYBRID-09** – Writer Guardrails       | Rewrite Writer in Outlines        | Trim length, strip markdown, add tests                    |
| **HYBRID-10** – E2E & Docs              | Improve summariser quality        | Produce benchmark report, update README                   |

---

### Workflow Checklist (post in every PR)

1. [ ] Story ID & description match backlog
2. [ ] No unrelated file changes
3. [ ] Unit tests added/updated
4. [ ] Metrics hook included (if agent changed)
5. [ ] Docs / ADR updated
6. [ ] DoD checklist passed
7. [ ] CI green

---

### Escalation Path

* **Daily stand-up**: raise blockers >4 h.
* **Friday demo**: show working slice increment.
* **Change-control**: PM + Lead Eng approve any scope change >½ day.

Stick to these guard-rails and the slice stays lean, predictable, and shippable.
