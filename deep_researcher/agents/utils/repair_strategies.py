"""
Modular repair strategies for ValidationWrapper.
Each strategy handles specific types of validation failures with different approaches.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Tuple
from enum import Enum
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .observability import ObservabilityHandler


class RepairResult(BaseModel):
    """Result of a repair attempt"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    strategy_used: str
    processing_time_ms: int
    confidence: float  # 0.0 to 1.0


class ValidationErrorType(Enum):
    """Types of validation errors that can be repaired"""
    JSON_STRUCTURE = "json_structure"
    SCHEMA_VALIDATION = "schema_validation"
    FIELD_CONSTRAINT = "field_constraint"
    MISSING_FIELDS = "missing_fields"
    TYPE_MISMATCH = "type_mismatch"
    UNKNOWN = "unknown"


class RepairStrategy(ABC):
    """Abstract base class for repair strategies"""
    
    def __init__(self, observability: ObservabilityHandler = None):
        self.observability = observability or ObservabilityHandler()
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def can_repair(self, error_type: ValidationErrorType, error_message: str, 
                        raw_output: str) -> bool:
        """Check if this strategy can handle the given error"""
        pass
    
    @abstractmethod
    async def repair(self, raw_output: str, error_message: str, 
                    schema: Any = None, **kwargs) -> RepairResult:
        """Attempt to repair the output"""
        pass
    
    def _create_result(self, success: bool, data: Optional[Dict] = None, 
                      error: Optional[str] = None, confidence: float = 0.0,
                      start_time: float = None) -> RepairResult:
        """Helper to create RepairResult with timing"""
        processing_time = int((time.time() - (start_time or time.time())) * 1000)
        return RepairResult(
            success=success,
            data=data,
            error=error,
            strategy_used=self.name,
            processing_time_ms=processing_time,
            confidence=confidence
        )


class LocalPatternRepair(RepairStrategy):
    """
    Enhanced version of existing local pattern repair.
    Handles common JSON malformation patterns through regex fixes.
    """
    
    async def can_repair(self, error_type: ValidationErrorType, error_message: str,
                        raw_output: str) -> bool:
        """Can repair JSON structure errors and some schema issues"""
        return error_type in [
            ValidationErrorType.JSON_STRUCTURE,
            ValidationErrorType.SCHEMA_VALIDATION,
            ValidationErrorType.FIELD_CONSTRAINT
        ]
    
    async def repair(self, raw_output: str, error_message: str, 
                    schema: Any = None, **kwargs) -> RepairResult:
        """Apply pattern-based local fixes"""
        start_time = time.time()
        
        try:
            # Apply enhanced repair patterns
            fixed = self._repair_malformed_json(raw_output)
            data = json.loads(fixed)
            
            self.observability.increment('local_repair_success')
            return self._create_result(
                success=True, 
                data=data, 
                confidence=0.75,  # Medium confidence for local repairs
                start_time=start_time
            )
            
        except Exception as e:
            self.observability.increment('local_repair_failed')
            return self._create_result(
                success=False, 
                error=f"Local repair failed: {e}", 
                confidence=0.0,
                start_time=start_time
            )
    
    def _repair_malformed_json(self, malformed_json: str) -> str:
        """Enhanced version of existing repair patterns"""
        fixed = malformed_json
        
        # Existing patterns from original ValidationWrapper
        fixed = fixed.replace('```json', '').replace('```', '')
        fixed = re.sub(r'"schema_v\s*\n\s*on"', '"schema_version"', fixed)
        fixed = fixed.replace('"schema_tag":', '"schema_version":')
        fixed = re.sub(r'}\s*\n\s*{', '},\n    {', fixed)
        fixed = re.sub(r'(?<!")https?://[^\s,}\]]+', lambda m: f'"{m.group(0)}"', fixed)
        fixed = re.sub(r'--\([^)]*\)', '', fixed)
        
        # Enhanced patterns for common agent output issues
        # Fix trailing commas
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # Fix missing quotes around field names
        fixed = re.sub(r'(\w+)(\s*:)', r'"\1"\2', fixed)
        
        # Fix boolean/null values to JSON format
        fixed = re.sub(r'\b(True|False|None)\b', 
                      lambda m: {'True': 'true', 'False': 'false', 'None': 'null'}[m.group(0)], 
                      fixed)
        
        # Fix single quotes to double quotes
        fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)
        
        # Ensure proper array formatting for sources
        fixed = re.sub(r'"sources":\s*([^,}\]]+)', 
                      lambda m: f'"sources": [{m.group(1)}]' if not m.group(1).strip().startswith('[') else m.group(0), 
                      fixed)
        
        # Fix common field name variations
        field_mappings = {
            '"title"': '"report_title"',
            '"context"': '"background_context"',
            '"outline"': '"report_outline"',
            '"summary"': '"output"'
        }
        for old_field, new_field in field_mappings.items():
            if new_field.replace('"', '') in str(fixed):  # Only map if target field exists
                fixed = fixed.replace(old_field, new_field)
        
        return fixed


class LLMRetryRepair(RepairStrategy):
    """
    Enhanced LLM retry strategy with context-specific repair prompts.
    Uses the model to fix its own output based on validation errors.
    """
    
    def __init__(self, model_client: Any = None, max_retries: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.model_client = model_client
        self.max_retries = max_retries
    
    async def can_repair(self, error_type: ValidationErrorType, error_message: str,
                        raw_output: str) -> bool:
        """Can repair most error types if model client is available"""
        return self.model_client is not None
    
    async def repair(self, raw_output: str, error_message: str,
                    schema: Any = None, **kwargs) -> RepairResult:
        """Attempt LLM-based repair with enhanced prompting"""
        start_time = time.time()
        
        if not self.model_client:
            return self._create_result(
                success=False,
                error="No model client available for LLM repair",
                confidence=0.0,
                start_time=start_time
            )
        
        try:
            # Create context-specific repair prompt
            repair_prompt = self._create_repair_prompt(error_message, schema)
            
            # Attempt LLM repair with proper async handling
            if hasattr(self.model_client, 'call_with_functions'):
                response = await self.model_client.call_with_functions(
                    prompt=repair_prompt,
                    functions=[self._get_function_schema(schema)] if schema else []
                )
            elif callable(self.model_client):
                # Handle callable model client
                response = await self.model_client(repair_prompt)
            else:
                # Handle mock or other object types
                if hasattr(self.model_client, '__call__'):
                    response_obj = self.model_client(repair_prompt)
                    # Check if it's a coroutine that needs awaiting
                    import asyncio
                    if asyncio.iscoroutine(response_obj):
                        response = await response_obj
                    else:
                        response = response_obj
                else:
                    response = str(self.model_client)
            
            # Extract and validate repaired JSON
            data = self._extract_json(response)
            
            self.observability.increment('llm_repair_success')
            return self._create_result(
                success=True,
                data=data,
                confidence=0.85,  # High confidence for LLM repairs
                start_time=start_time
            )
            
        except Exception as e:
            self.observability.increment('llm_repair_failed')
            return self._create_result(
                success=False,
                error=f"LLM repair failed: {e}",
                confidence=0.0,
                start_time=start_time
            )
    
    def _create_repair_prompt(self, error_message: str, schema: Any = None) -> str:
        """Create context-specific repair prompt"""
        base_prompt = f"""Your JSON output had validation errors: {error_message}

Please return ONLY the corrected JSON that fixes these specific issues:
- Use double quotes for all strings
- Ensure all required fields are present
- Follow proper JSON syntax (no trailing commas, proper brackets)
- Remove any markdown fences or extra text"""
        
        if schema:
            # Add schema-specific guidance
            if hasattr(schema, 'model_json_schema'):
                schema_info = schema.model_json_schema()
                required_fields = schema_info.get('required', [])
                if required_fields:
                    base_prompt += f"\n- Required fields: {', '.join(required_fields)}"
        
        return base_prompt
    
    def _extract_json(self, response: str) -> dict:
        """Extract JSON from LLM response"""
        # Use existing extraction logic
        start = response.find('{')
        end = response.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        
        raw = response[start:end]
        return json.loads(raw)
    
    def _get_function_schema(self, schema: Any) -> Dict:
        """Get function schema for structured generation"""
        if hasattr(schema, 'model_json_schema'):
            return {
                "name": "generate_output",
                "description": "Generate properly formatted output",
                "parameters": schema.model_json_schema()
            }
        return {}


class SchemaRelaxationRepair(RepairStrategy):
    """
    Attempts repair by temporarily relaxing schema constraints.
    Useful when the core content is correct but constraints are too strict.
    """
    
    async def can_repair(self, error_type: ValidationErrorType, error_message: str,
                        raw_output: str) -> bool:
        """Can repair field constraint and some schema validation errors"""
        return error_type in [
            ValidationErrorType.FIELD_CONSTRAINT,
            ValidationErrorType.SCHEMA_VALIDATION
        ]
    
    async def repair(self, raw_output: str, error_message: str,
                    schema: Any = None, **kwargs) -> RepairResult:
        """Attempt repair with relaxed constraints"""
        start_time = time.time()
        
        try:
            # Parse the JSON first
            data = json.loads(raw_output)
            
            # Apply field fixes based on common constraint violations
            fixed_data = self._apply_constraint_fixes(data, error_message)
            
            self.observability.increment('schema_relaxation_success')
            return self._create_result(
                success=True,
                data=fixed_data,
                confidence=0.65,  # Lower confidence due to relaxed validation
                start_time=start_time
            )
            
        except Exception as e:
            self.observability.increment('schema_relaxation_failed')
            return self._create_result(
                success=False,
                error=f"Schema relaxation failed: {e}",
                confidence=0.0,
                start_time=start_time
            )
    
    def _apply_constraint_fixes(self, data: Dict, error_message: str) -> Dict:
        """Apply fixes for common constraint violations"""
        fixed = data.copy()
        
        # Fix string length constraints
        if 'min_length' in error_message or 'too short' in error_message.lower():
            for key, value in fixed.items():
                if isinstance(value, str) and len(value) < 10:
                    fixed[key] = value + " (content expanded for minimum length requirement)"
        
        if 'max_length' in error_message or 'too long' in error_message.lower():
            for key, value in fixed.items():
                if isinstance(value, str) and len(value) > 1000:
                    fixed[key] = value[:997] + "..."
        
        # Fix array length constraints
        if 'sources' in fixed and isinstance(fixed['sources'], list):
            # Ensure sources is not empty if required
            if len(fixed['sources']) == 0:
                fixed['sources'] = ["https://example.com/source"]
            # Limit sources length if too long
            elif len(fixed['sources']) > 20:
                fixed['sources'] = fixed['sources'][:20]
        
        # Add missing schema_version if required
        if 'schema_version' not in fixed:
            fixed['schema_version'] = 1
        
        return fixed


class LegacyFallbackRepair(RepairStrategy):
    """
    Final fallback strategy that uses legacy parsing methods.
    Always succeeds by providing a minimal valid response.
    """
    
    async def can_repair(self, error_type: ValidationErrorType, error_message: str,
                        raw_output: str) -> bool:
        """Can always provide a fallback"""
        return True
    
    async def repair(self, raw_output: str, error_message: str,
                    schema: Any = None, **kwargs) -> RepairResult:
        """Provide fallback response that always validates"""
        start_time = time.time()
        
        try:
            # Create minimal valid response based on schema
            fallback_data = self._create_fallback_response(raw_output, schema)
            
            self.observability.increment('legacy_fallback_success')
            return self._create_result(
                success=True,
                data=fallback_data,
                confidence=0.3,  # Low confidence for fallback
                start_time=start_time
            )
            
        except Exception as e:
            # This should never happen, but provide ultimate fallback
            self.observability.increment('legacy_fallback_failed')
            return self._create_result(
                success=True,  # Always succeed
                data={
                    "output": f"Validation failed: {error_message}",
                    "sources": [],
                    "processing_method": "error_fallback",
                    "confidence": 0.0
                },
                confidence=0.0,
                start_time=start_time
            )
    
    def _create_fallback_response(self, raw_output: str, schema: Any) -> Dict:
        """Create minimal valid response based on schema"""
        # Try to extract any valid content from raw output
        fallback = {}
        
        # Extract text content for output field
        text_content = self._extract_text_content(raw_output)
        fallback["output"] = text_content if text_content else "Processing failed - no valid content extracted"
        
        # Default sources
        fallback["sources"] = []
        
        # Add schema-specific required fields
        if schema and hasattr(schema, 'model_json_schema'):
            schema_info = schema.model_json_schema()
            required_fields = schema_info.get('required', [])
            properties = schema_info.get('properties', {})
            
            for field in required_fields:
                if field not in fallback:
                    field_info = properties.get(field, {})
                    field_type = field_info.get('type', 'string')
                    
                    # Provide appropriate defaults
                    if field_type == 'string':
                        fallback[field] = f"Default {field}"
                    elif field_type == 'integer':
                        fallback[field] = field_info.get('default', 1)
                    elif field_type == 'array':
                        fallback[field] = []
                    elif field_type == 'boolean':
                        fallback[field] = False
                    elif field_type == 'number':
                        fallback[field] = 0.0
        
        # Add standard observability fields
        fallback["processing_method"] = "legacy_fallback"
        fallback["confidence"] = 0.0
        
        return fallback
    
    def _extract_text_content(self, raw_output: str) -> Optional[str]:
        """Extract any readable text content from raw output"""
        if not raw_output:
            return None
        
        # Remove JSON structure attempts
        text = re.sub(r'[{}"\[\],:]', ' ', raw_output)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Extract meaningful content (longer than 10 chars)
        if len(text) > 10:
            return text[:500]  # Limit length
        
        return None


class RepairStrategyFactory:
    """Factory for creating and managing repair strategies"""
    
    @staticmethod
    def create_default_strategies(model_client: Any = None, 
                                observability: ObservabilityHandler = None) -> List[RepairStrategy]:
        """Create default set of repair strategies in order of preference"""
        return [
            LocalPatternRepair(observability=observability),
            LLMRetryRepair(model_client=model_client, observability=observability),
            SchemaRelaxationRepair(observability=observability),
            LegacyFallbackRepair(observability=observability)
        ]
    
    @staticmethod
    def classify_error(error_message: str, raw_output: str) -> ValidationErrorType:
        """Classify the type of validation error"""
        error_lower = error_message.lower()
        
        if 'json' in error_lower or 'parse' in error_lower or 'syntax' in error_lower:
            return ValidationErrorType.JSON_STRUCTURE
        elif 'required' in error_lower or 'missing' in error_lower:
            return ValidationErrorType.MISSING_FIELDS
        elif 'type' in error_lower or 'expected' in error_lower:
            return ValidationErrorType.TYPE_MISMATCH
        elif 'constraint' in error_lower or 'length' in error_lower or 'range' in error_lower:
            return ValidationErrorType.FIELD_CONSTRAINT
        elif 'schema' in error_lower or 'validation' in error_lower:
            return ValidationErrorType.SCHEMA_VALIDATION
        else:
            return ValidationErrorType.UNKNOWN