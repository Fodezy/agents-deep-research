# 🎫 HYBRID-02: ValidationWrapper + Observability - Implementation Plan

Based on the QA guardrails and HYBRID-01 deliverables, here's the focused plan for HYBRID-02.

## Scope Definition (Per Guardrails)

**✅ Must Deliver:**

* `ValidationWrapper` (working, not perfect; uses `schemas.validator` for core JSON extraction)
* `ObservabilityHandler` with in-memory, schema-tagged counters
* `llm_config` ability to pass `functions` list (graceful if env var off)
* Unit tests for **5** malformed samples
* **NO agent refactors yet** (they’re HYBRID-05+)

**Success Gate:** repair **≥ 3 / 5** samples
--- 

**❌ Out of Scope:**
- Prometheus integration → metrics stub only
- Fancy retry strategies (single retry rule stands)
- Agent conversions to Outlines
- Performance optimization

**📏 Budget Constraints:**
- `validation_wrapper.py` ≤ 200 LoC
- `observability.py` ≤ 120 LoC
- 5-day delivery timeline

## Implementation Tasks

### Day 1–2: Core ValidationWrapper

**File:** `deep_researcher/agents/utils/validation_wrapper.py`

```python
class ValidationWrapper:
    def __init__(self, schema_name: str, observability: ObservabilityHandler):
        self.schema_name = schema_name
        self.validator = schemas.validator  # auto‐discover schemas
        self.observability = observability

    async def validate_and_repair(self, llm_response: str, model_client: Any) -> dict:
        # 1. _extract_json → use schemas.validator to locate JSON
        try:
            data = self._extract_json(llm_response)
            valid, err = self._validate_with_schema(data)
        except JSONExtractionError:
            self.observability.increment('json_extraction_failed', {'schema': self.schema_name})
            data = self._repair_malformed_json(llm_response)
            valid, err = self._validate_with_schema(data)
        if not valid:
            self.observability.increment('validation_failed', {'schema': self.schema_name})
            repaired = await self._attempt_single_retry(model_client, err)
            data = self._extract_json(repaired)
            valid, err = self._validate_with_schema(data)
            self.observability.increment('repair_success' if valid else 'repair_failed',
                                         {'schema': self.schema_name})
        else:
            self.observability.increment('validation_success', {'schema': self.schema_name})
        return data

    def _repair_malformed_json(self, text: str) -> str:
        # Delegate to schemas.validator when possible for known patterns,
        # fallback to local regex for missing commas, quotes, newline fixes.
        repaired = schemas.validator.auto_repair(text, self.schema_name)
        return repaired
```

**Core Logic Flow:**
1. Extract JSON from LLM response
2. Validate against schema using `schemas.validator`
3. On failure → apply local repairs (newlines, quotes, commas)
4. If still invalid → single retry with model feedback
5. Emit metrics at each step

### Day 2–3: ObservabilityHandler

**File:** `deep_researcher/agents/utils/observability.py`

```python
class ObservabilityHandler:
    def __init__(self):
        self.counters = defaultdict(lambda: defaultdict(int))
        self.timers = {}

    def increment(self, counter_name: str, tags: dict = None):
        tags = tags or {}
        key = tuple(sorted(tags.items()))
        self.counters[counter_name][key] += 1

    def record_time(self, timer_name: str, duration_ms: float, tags: dict = None):
        # optional: store histograms or lists per tag
        pass

    def log_validation_failure(self, model_name: str, error_type: str, details: dict):
        print(f"[ValidationFailure][{model_name}][{error_type}] {details}")

    def get_metrics_summary(self) -> dict:
        return {cn: dict(tagmap) for cn, tagmap in self.counters.items()}

    def reset_metrics(self):
        self.counters.clear()
```

*Counters are now tagged by `{'schema': schema_name}` so you can break down failures per agent.*

---

### Day 3–4: LLM Config Integration

**File:** `deep_researcher/llm_config.py`

```python
class LLMConfig:
    def call_with_functions(self, model_client: Any, prompt: str, functions: List[dict]) -> Any:
        enable = os.getenv("ENABLE_FUNCTION_CALLING", "false").lower() == "true"
        if enable and hasattr(model_client, "chat_completion_with_functions"):
            return model_client.chat_completion_with_functions(prompt=prompt, functions=functions)
        else:
            # fallback to plain chat
            return model_client.chat_completion(prompt=prompt)
```

*No error if env var missing, and falls back automatically when function‐calling unsupported.*

--- 
### Day 4: Unit Tests

**File: `tests/test_validation_wrapper.py`**

Test cases for each malformed sample:
```python
def test_repair_newline_in_field_name()
def test_repair_missing_comma()
def test_repair_unquoted_url()
def test_repair_schema_typo() 
def test_repair_comment_injection()
def test_metrics_emission()
def test_single_retry_logic()
```

**Success Gate:** ≥ 2/3 malformed samples must be repaired successfully

### Day 5: Integration & Testing

* Wire `ValidationWrapper` into agents.
* **Add a smoke test** in CI: e.g. in `tests/test_smoke_validation.py` call one real agent through the wrapper to catch wiring issues.
* Ensure CI runs `scripts/validate_sample.py` over all 5 samples.
* Tag release `v0.2.0`.

---

## Implementation Details

### JSON Repair Logic (Local Fixes)
```python
def _repair_malformed_json(self, malformed_json: str) -> str:
    # 1. Remove markdown fences
    # 2. Fix newlines in field names: "schema_v\n\non" → "schema_version"  
    # 3. Fix missing commas: }\n{ → },\n{
    # 4. Fix unquoted URLs: https://... → "https://..."
    # 5. Fix field typos: "schema_tag" → "schema_version"
    # 6. Remove invalid comments: --(comment) → ""
```

### Retry Strategy (Single Attempt)
```python
async def _attempt_single_retry(self, model_client: Any, error: str) -> str:
    repair_prompt = f"""Your JSON had validation errors: {error}
    
Please provide ONLY corrected JSON matching the required schema.
- Use double quotes for all strings
- Include required schema_version: 1
- Remove any markdown fences
- Ensure proper comma placement"""
    
    return await self.llm_config.call_with_functions(
        model_client, repair_prompt, [self.function_schema]
    )
```

## Success Criteria

**Must Pass CI:**
- `pytest tests/test_validation_wrapper.py` → Green
- Wrapper repairs ≥ 2/3 malformed samples
- `validator.list_schemas()` auto-detects all schemas
- All metrics counters increment properly

**Demo Checkpoints:**
- **Day 2:** ValidationWrapper validates & repairs JSON parsing errors
- **Day 4:** All 5 malformed samples tested, metrics printed
- **Day 5:** PR merged, tagged release

## Files to Create/Modify

```
deep_researcher/
├── agents/utils/
│   ├── validation_wrapper.py     # New - Core wrapper logic
│   └── observability.py          # New - Metrics collection
├── llm_config.py                 # Modified - Add function calling
└── ...

tests/
└── test_validation_wrapper.py    # New - Unit tests

scripts/
└── validate_sample.py            # New - CLI testing tool
```

## Risk Mitigation

1. **Scope Creep Risk:** Stick to malformed JSON repair only, no agent conversions
2. **Complexity Risk:** Single retry maximum, no exponential backoff
3. **Time Risk:** Use existing malformed samples, don't create new test cases
4. **Integration Risk:** Keep existing agent APIs unchanged

## Implementation Notes

### ValidationWrapper Design
- Accept schema_name in constructor
- Load schema from `schemas.validator` automatically
- Use `schemas.models` for Pydantic validation
- Emit metrics via ObservabilityHandler instance
- Keep existing agent APIs unchanged

### ObservabilityHandler Design
- In-memory counters only (no external systems)
- Thread-safe increment operations
- Simple dict-based storage
- Console logging for validation failures
- Reset capability for unit tests

### LLM Config Integration
- Add optional `call_with_functions` method
- Check `ENABLE_FUNCTION_CALLING` environment variable
- Graceful fallback when functions not supported
- Preserve existing model initialization logic

## Testing Strategy

1. **Unit Tests:** Each malformed sample type
2. **Integration Tests:** ValidationWrapper with real schemas
3. **Metrics Tests:** Counter increments and timing
4. **CLI Testing:** Manual validation script for QA

## Definition of Done

- [ ] ValidationWrapper class implemented (≤200 LoC)
- [ ] ObservabilityHandler class implemented (≤120 LoC)
- [ ] LLM config function calling support added
- [ ] Unit tests pass for ≥2/3 malformed samples
- [ ] CLI validation script working
- [ ] All metrics counters functioning
- [ ] CI pipeline green
- [ ] PR reviewed and merged
- [ ] Release v0.2.0 tagged

**Ready to start HYBRID-02?** This focused plan should deliver working validation within the 5-day timeline while respecting all guardrails.