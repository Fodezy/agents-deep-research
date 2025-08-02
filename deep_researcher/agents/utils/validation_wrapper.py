import json
import time
import re
from typing import Any, Tuple, Callable, Awaitable, List
from schemas.validator import validator
from .observability import ObservabilityHandler

class ValidationWrapper:
    """
    Intercepts LLM outputs for JSON-emitting agents, validates against JSON schemas
    and performs a single auto-repair attempt on failure, emitting observability metrics.
    """
    def __init__(
        self,
        schema_name: str,
        agent_name: str,
        call_with_functions: Callable[..., Awaitable[str]],
        observability: ObservabilityHandler = None,
    ):
        self.schema_name = schema_name
        self.agent_name = agent_name
        self.call_with_functions = call_with_functions
        self.function_schema = validator.get_schema(schema_name)
        self.observability = observability or ObservabilityHandler()

    async def validate_and_repair(self, llm_response: str, model_client: Any) -> dict:
        """
        Extracts JSON from LLM response, validates it, attempts
        a local repair + one LLM retry if necessary, and returns validated dict.
        Raises ValueError if still invalid.
        """
        # --- JSON Extraction ---
        start = time.time()
        try:
            data = self._extract_json(llm_response)
            self.observability.increment('json_extraction_success')
        except Exception:
            self.observability.increment('json_extraction_failed')
            raise
        finally:
            self.observability.record_time('extraction_latency_ms', (time.time() - start) * 1000)

        # --- Initial Validation ---
        start = time.time()
        valid, error = self._validate_with_schema(data)
        self.observability.record_time('validation_latency_ms', (time.time() - start) * 1000)
        if valid:
            self.observability.increment('validation_success')
            return data

        self.observability.increment('validation_failed')

        # --- Local Repair Attempt ---
        start = time.time()
        malformed = json.dumps(data)
        repaired = self._repair_malformed_json(malformed)
        try:
            data = json.loads(repaired)
            self.observability.increment('repair_local_applied')
        except Exception:
            self.observability.increment('repair_local_failed')
            data = {}
        self.observability.record_time('local_repair_latency_ms', (time.time() - start) * 1000)

        # --- Re-validation after Local Repair ---
        valid, error = self._validate_with_schema(data)
        if valid:
            self.observability.increment('repair_success')
            return data

        self.observability.increment('repair_failed')

        # --- LLM Retry Attempt ---
        start = time.time()
        retry_response = await self._attempt_single_retry(model_client, error)
        self.observability.record_time('retry_latency_ms', (time.time() - start) * 1000)

        # Extract & validate retry outcome
        data = self._extract_json(retry_response)
        valid, error = self._validate_with_schema(data)
        if valid:
            self.observability.increment('repair_success')
            return data

        self.observability.increment('repair_failed')
        raise ValueError(f"Validation failed after retry: {error}")

    def _extract_json(self, response: str) -> dict:
        """
        Pulls and lightly repairs the JSON object from the LLM text.
        """
        # find the outer braces
        start = response.find('{')
        end   = response.rfind('}') + 1
        raw   = response[start:end]

        # auto-repair before parsing so extract_json succeeds on malformed
        raw = self._repair_malformed_json(raw)
        return json.loads(raw)

    def _validate_with_schema(self, data: dict) -> Tuple[bool, str]:
        """Validate data against the schema"""
        valid, error_msg, validation_error = validator.validate(self.schema_name, data)
        return valid, error_msg or ''

    def _repair_malformed_json(self, malformed_json: str) -> str:
        """
        Apply lightweight, local fixes to common JSON malformations.
        """
        fixed = malformed_json
        # 1. Strip markdown fences
        fixed = fixed.replace('```json', '').replace('```', '')
        # 2. Fix common newline-in-key patterns
        fixed = re.sub(r'"schema_v\s*\n\s*on"', '"schema_version"', fixed)
        # 3. Fix field name typos
        fixed = fixed.replace('"schema_tag":', '"schema_version":')
        # 4. Ensure commas between objects - more robust pattern
        fixed = re.sub(r'}\s*\n\s*{', '},\n    {', fixed)
        # 5. Wrap bare URLs in quotes
        fixed = re.sub(r'(?<!")https?://[^\s,}\]]+', lambda m: f'"{m.group(0)}"', fixed)
        # 6. Remove inline comments
        fixed = re.sub(r'--\([^)]*\)', '', fixed)
        return fixed

    async def _attempt_single_retry(self, model_client: Any, error: str) -> str:
        prompt = (
            f"Your JSON had validation errors: {error}\n\n"
            "Please return ONLY the corrected JSON matching the schema:\n"
            "- Use double quotes for all strings\n"
            "- Include required schema_version: 1\n"
            "- Remove any markdown fences\n"
            "- Ensure proper comma placement\n"
        )
        return await model_client.call_with_functions(
            prompt=prompt,
            functions=[self.function_schema]
        )
