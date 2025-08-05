import json
import re
from typing import Any, Callable, List, Dict
from pydantic import BaseModel, ValidationError

class OutputParserError(Exception):
    def __init__(self, message, output=None):
        self.message = message
        self.output = output
        super().__init__(self.message)
    def __str__(self):
        if self.output:
            return f"{self.message}\nProblematic output: {self.output}"
        return self.message

def find_all_json_in_string(string: str) -> List[str]:
    # Remove thinking tags that some models include
    string = re.sub(r'<think>.*?</think>', '', string, flags=re.DOTALL)
    
    code_block_pattern = r'```(?:json)?\s*(.*?)```'
    code_blocks = re.findall(code_block_pattern, string, re.DOTALL)
    candidates = [string] + code_blocks
    results: List[str] = []
    for s in candidates:
        depth = 0
        start = None
        for i, ch in enumerate(s):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    blob = s[start : i+1]
                    if blob not in results:
                        results.append(blob)
                    start = None
    return results

def create_type_parser(model: type[BaseModel]) -> Callable[[str], BaseModel]:
    """
    Parses raw LLM output into JSON, normalizes keys, wraps unquoted tokens in quotes,
    and validates with Pydantic.
    """
    def parser(raw: str) -> BaseModel:
        last_err = None
        found_function_call = False

        for blob in find_all_json_in_string(raw):
            # 1) Attempt to parse JSON directly
            try:
                data = json.loads(blob)
            except json.JSONDecodeError as e:
                # 1a) Fix stray asterisks on keys
                fixed_blob = re.sub(r'\*(\w+)":', r'"\1":', blob)
                # 1b) Fix Python literals to JSON literals
                fixed_blob = re.sub(r'\bnone\b', 'null', fixed_blob, flags=re.IGNORECASE)
                fixed_blob = re.sub(r'\bTrue\b', 'true', fixed_blob)
                fixed_blob = re.sub(r'\bFalse\b', 'false', fixed_blob)
                
                # 1c) Wrap unquoted string values in quotes
                unq_pattern = re.compile(
                    r'("(?P<key>[^"]+)"\s*:\s*)'        # "key":
                    r'(?!["\d]|true|false|null)'       # not quoted, digit, bool or null
                    r'(?P<val>[^,\}\n]+)'              # unquoted value
                )
                fixed_blob = unq_pattern.sub(
                    lambda m: f'{m.group(1)}"{m.group("val").strip()}"',
                    fixed_blob
                )
                # 1d) Retry loading JSON
                try:
                    data = json.loads(fixed_blob)
                except json.JSONDecodeError:
                    last_err = e
                    continue

            # ────────────────────────────────────────────────────────────────────
            # Wrap bare task lists into the dict the AgentSelectionPlan expects
            if isinstance(data, list) and "tasks" in model.model_fields:
                data = {"tasks": data}
            # -----------------------------------------------------------------------

            # ---------------------------------------------------------------
            # Normalize root keys for PlannerAgent
            if "title" in data and "report_title" not in data:
                data["report_title"] = data.pop("title")
            
            # Handle missing report_outline - create empty outline if not provided
            if "report_title" in data and "report_outline" not in data:
                data["report_outline"] = []

            if "outline" in data and "report_outline" not in data:
                outline = data.pop("outline")
                if isinstance(outline, dict):
                    report_outline: List[Dict[str, Any]] = []
                    for sec_title, details in outline.items():
                        q = None
                        if isinstance(details, dict):
                            q = details.get("Key Question") or details.get("key_question")
                        report_outline.append({"title": sec_title, "key_question": q})
                    data["report_outline"] = report_outline

            if "sections" in data and "report_outline" not in data:
                secs = data.pop("sections")
                if isinstance(secs, list):
                    data["report_outline"] = secs

            # **NEW** handle nested planner output
            if "report_plan" in data and "report_outline" not in data:
                rp = data.pop("report_plan")
                sections = rp.get("section_titles_and_questions") or rp.get("report_outline")
                if isinstance(sections, list):
                    data["report_outline"] = [
                        {"title": sec.get("title"), "key_question": sec.get("key_question")}
                        for sec in sections
                    ]

            # **NEW** normalize dict-style report_outline   list
            if "report_outline" in data and isinstance(data["report_outline"], dict):
                outline_dict = data.pop("report_outline")
                normalized = []
                for sec_title, questions in outline_dict.items():
                    title = sec_title.strip()
                    if isinstance(questions, list):
                        for q in questions:
                            normalized.append({"title": title, "key_question": q})
                    else:
                        normalized.append({"title": title, "key_question": questions})
                data["report_outline"] = normalized

            # Normalize keys for AgentSelectionPlan
            if "sections" in data and "tasks" not in data:
                data["tasks"] = data.pop("sections")
            # ---------------------------------------------------------------

            # 2) Skip pure JSON-schema blobs
            if isinstance(data, dict) and all(k in data for k in ("properties", "required", "type")):
                continue
            
            # 2b) Skip function call JSON (has "name" and "arguments"/"parameters")
            if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
                found_function_call = True
                continue

            # 3) Try direct Pydantic validation
            try:
                return model.model_validate(data)
            except ValidationError as e:
                last_err = e

            # 4) Unwrap properties envelope
            if isinstance(data, dict) and "properties" in data:
                props = data["properties"]
                if isinstance(props, dict) and not all(isinstance(v, dict) and "type" in v for v in props.values()):
                    norm = {}
                    for k, v in props.items():
                        match = next((f for f in model.model_fields if f.lower() == k.lower()), None)
                        norm_key = match or k
                        norm[norm_key] = v
                    try:
                        return model.model_validate(norm)
                    except ValidationError as e:
                        last_err = e
                        continue

        # Enhanced error message when only function call JSON was found
        error_msg = f"Failed to parse and validate output as {model.__name__}"
        if found_function_call:
            import os
            fc_enabled = os.getenv("ENABLE_FUNCTION_CALLING", "true").lower() in ("1", "true")
            if not fc_enabled:
                error_msg += ". Found function call JSON but ENABLE_FUNCTION_CALLING is disabled - tools may not have executed."
            else:
                error_msg += ". Found function call JSON but no valid output afterward - tool execution may have failed."
        
        raise OutputParserError(error_msg, raw)

    return parser
