import pytest
import json
from unittest.mock import AsyncMock

from deep_researcher.agents.utils.validation_wrapper import ValidationWrapper
from deep_researcher.agents.utils.observability import ObservabilityHandler
from schemas.validator import validator

# Load and index our malformed samples fixture
with open('TODO/malformed_samples.json') as f:
    raw = json.load(f)
    MALFORMED = {item["name"]: item for item in raw["test_samples"]}


@pytest.fixture
def observability():
    return ObservabilityHandler()


@pytest.fixture
def mock_model_client():
    client = AsyncMock()
    # simulate call_with_functions returning a corrected JSON
    async def _fake_call_with_functions(prompt, functions):
        return json.dumps({
            "schema_version": 1,
            "tasks": [
                {
                    "gap": "A fixed gap",
                    "agent": "WebSearchAgent",
                    "query": "fixed query",
                    "entity_website": None
                }
            ]
        })
    client.call_with_functions = AsyncMock(side_effect=_fake_call_with_functions)
    return client


def test_extract_json_basic(observability):
    wrapper = ValidationWrapper(
        schema_name="select_tools",
        agent_name="ToolSelectorAgent",
        call_with_functions=lambda *a, **k: None,
        observability=observability
    )
    text = (
        "Here is some explanation\n```json\n"
        + MALFORMED["missing_comma_between_objects"]["input"]
        + "\n``` More text"
    )
    data = wrapper._extract_json(text)
    assert isinstance(data, dict)
    assert "tasks" in data


@pytest.mark.parametrize("sample_key", [
    "newline_in_field_name",
    "missing_comma_between_objects",
    "unquoted_url_and_markdown_fences",
])
def test_local_repair_can_fix(sample_key, observability):
    wrapper = ValidationWrapper(
        schema_name=MALFORMED[sample_key]["schema"],
        agent_name="SomeAgent",
        call_with_functions=lambda *a, **k: None,
        observability=observability
    )
    malformed = MALFORMED[sample_key]["input"]
    repaired = wrapper._repair_malformed_json(malformed)
    # After repair it should at least parse as JSON (even if it doesn't yet satisfy schema)
    parsed = json.loads(repaired)
    assert isinstance(parsed, dict)


def test_validation_success_no_repair(observability):
    valid = {
        "schema_version": 1,
        "tasks": [
            {
                "gap": "This is a test gap that meets minimum length requirements",
                "agent": "WebSearchAgent",
                "query": "test query",
                "entity_website": None
            }
        ]
    }
    wrapper = ValidationWrapper(
        schema_name="select_tools",
        agent_name="ToolSelectorAgent",
        call_with_functions=lambda *a, **k: None,
        observability=observability
    )
    valid_flag, _ = wrapper._validate_with_schema(valid)
    assert valid_flag


@pytest.mark.asyncio
async def test_validate_and_repair_local_and_retry(observability, mock_model_client):
    # This sample has a typo in schema_version field name, local repair should fix it
    sample = MALFORMED["schema_version_typo"]["input"]
    wrapper = ValidationWrapper(
        schema_name="create_plan",  # Use correct schema for this sample
        agent_name="PlannerAgent",
        call_with_functions=mock_model_client.call_with_functions,
        observability=observability
    )
    
    # Mock should return a valid create_plan schema response
    async def _fake_plan_call(prompt, functions):
        return json.dumps({
            "schema_version": 1,
            "report_title": "Fixed Report Title",
            "background_context": "Fixed background context for the research report that meets minimum length requirements.",
            "report_outline": [
                {
                    "title": "Fixed Section One",
                    "key_question": "What is the first fixed research question?"
                },
                {
                    "title": "Fixed Section Two", 
                    "key_question": "What is the second fixed research question?"
                }
            ]
        })
    mock_model_client.call_with_functions = AsyncMock(side_effect=_fake_plan_call)
    
    llm_text = f"```json\n{sample}\n```"
    result = await wrapper.validate_and_repair(llm_text, model_client=mock_model_client)

    # After repair, we should get the correctly repaired dict
    assert result["schema_version"] == 1
    assert "report_title" in result

    metrics = observability.get_metrics_summary()["counters"]
    # Local repair should fix the schema_tag -> schema_version issue
    assert metrics.get("validation_success", 0) > 0 or metrics.get("repair_success", 0) > 0


def test_observability_summary_and_reset(observability):
    observability.increment("test_counter", {"a": "1"})
    observability.record_time("test_timer", 123.4)
    observability.log_validation_failure("AgentX", "schema_error", {"field": "foo"})
    summary = observability.get_metrics_summary()

    assert "test_counter" in summary["counters"]
    assert "test_timer" in summary["timers_ms"]
    assert "AgentX" in summary["failures"]

    observability.reset_metrics()
    empty = observability.get_metrics_summary()
    assert empty["counters"] == {}
    assert empty["timers_ms"] == {}
    assert empty["failures"] == {}
