import json
import time
import re
from typing import Any, Tuple, Callable, Awaitable, List, Dict, Optional
from schemas.validator import validator
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .observability import ObservabilityHandler
# Production imports
from .validation_metrics import record_validation_metric
from .validation_logging import get_validation_logger, validation_context
from .production_config import get_production_config
from .repair_strategies import (
    RepairStrategy, RepairResult, RepairStrategyFactory, ValidationErrorType
)
from .circuit_breaker import ValidationCircuitBreaker, get_circuit_breaker_registry
from .validation_config import ValidationConfig, get_validation_config_manager

class ValidationWrapper:
    """
    Enhanced validation wrapper with modular repair strategies, circuit breaker protection,
    and comprehensive error recovery. Supports both legacy and new Pydantic schema validation.
    """
    
    def __init__(
        self,
        agent_name: str,
        schema: Optional[BaseModel] = None,
        schema_name: Optional[str] = None,
        call_with_functions: Optional[Callable[..., Awaitable[str]]] = None,
        config: Optional[ValidationConfig] = None,
        observability: Optional[ObservabilityHandler] = None,
    ):
        self.agent_name = agent_name
        self.schema = schema
        self.schema_name = schema_name
        self.call_with_functions = call_with_functions
        self.observability = observability or ObservabilityHandler()
        
        # Get configuration (production-aware)
        if config is None:
            # Use production config if available, fallback to validation config
            try:
                prod_config = get_production_config(agent_name)
                from .validation_config import ValidationConfig
                config = ValidationConfig(
                    enabled=prod_config.enabled,
                    mode=ValidationConfig().mode,
                    max_retries=prod_config.max_retries,
                    timeout_ms=prod_config.timeout_ms,
                    repair_strategies=prod_config.repair_strategies_enabled
                )
            except Exception:
                config_manager = get_validation_config_manager()
                config = config_manager.get_config(agent_name)
        
        self.config = config
        
        # Initialize production logging
        self.logger = get_validation_logger()
        
        # Initialize circuit breaker
        breaker_registry = get_circuit_breaker_registry()
        self.circuit_breaker = breaker_registry.get_breaker(
            agent_name, self.config.circuit_breaker
        )
        
        # Initialize repair strategies
        self.repair_strategies = RepairStrategyFactory.create_default_strategies(
            model_client=call_with_functions,
            observability=self.observability
        )
        
        # Legacy schema support
        if schema_name and not schema:
            try:
                self.function_schema = validator.get_schema(schema_name)
                self.legacy_mode = True
            except Exception:
                print(f"[ValidationWrapper] Warning: Could not load schema {schema_name}")
                self.function_schema = None
                self.legacy_mode = True
        else:
            self.legacy_mode = False
            self.function_schema = None
        
        print(f"[ValidationWrapper] Initialized for {agent_name} - enabled: {self.config.enabled}")

    async def validate_and_repair(self, llm_response: str, model_client: Any = None) -> Dict[str, Any]:
        """
        Enhanced validation with circuit breaker protection and modular repair strategies.
        """
        # Production logging context
        with validation_context(self.agent_name, "validate_and_repair") as logger:
            logger.log_validation_start(self.agent_name, llm_response)
            
            # Check if validation is disabled or circuit breaker is open
            if not self.config.enabled:
                return self._create_bypass_response(llm_response, "validation_disabled")
            
            if not self.circuit_breaker.should_allow_validation():
                return self._create_bypass_response(llm_response, "circuit_breaker_open")
            
            start_time = time.time()
            
            try:
                # Extract JSON from response
                data = await self._extract_json_with_timing(llm_response)
                
                # Initial validation
                is_valid, error_message = await self._validate_data(data)
                if is_valid:
                    processing_time_ms = (time.time() - start_time) * 1000
                    self.circuit_breaker.record_success()
                    self.observability.increment(f'validation.{self.agent_name}.success')
                    
                    # Record production metrics
                    record_validation_metric(
                        agent_name=self.agent_name,
                        validation_result="success",
                        processing_time_ms=processing_time_ms,
                        confidence=0.95
                    )
                    logger.log_validation_success(self.agent_name, processing_time_ms, 0.95)
                    
                    return self._create_success_response(data, "initial_validation", start_time)
                
                # Validation failed - attempt repairs
                return await self._attempt_repairs(
                    raw_output=llm_response,
                    initial_data=data,
                    error_message=error_message,
                    model_client=model_client or self.call_with_functions,
                    start_time=start_time
                )
                
            except Exception as e:
                processing_time_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                self.circuit_breaker.record_failure(error_msg)
                self.observability.increment(f'validation.{self.agent_name}.error')
                
                # Record production metrics
                record_validation_metric(
                    agent_name=self.agent_name,
                    validation_result="error",
                    processing_time_ms=processing_time_ms,
                    error_type=type(e).__name__,
                    confidence=0.0
                )
                logger.log_validation_error(
                    self.agent_name, type(e).__name__, error_msg, processing_time_ms, llm_response
                )
                
                # Return error fallback response
                return self._create_error_response(error_msg, start_time)

    async def _attempt_repairs(self, raw_output: str, initial_data: Dict, 
                             error_message: str, model_client: Any, 
                             start_time: float) -> Dict[str, Any]:
        """Attempt repairs using configured strategies"""
        
        # Classify error type
        error_type = RepairStrategyFactory.classify_error(error_message, raw_output)
        
        # Try each repair strategy in order
        for strategy in self.repair_strategies:
            if not await strategy.can_repair(error_type, error_message, raw_output):
                continue
                
            self.observability.increment(f'repair.{self.agent_name}.{strategy.name}.attempt')
            
            try:
                # Update model client for LLM strategies
                if hasattr(strategy, 'model_client') and model_client:
                    strategy.model_client = model_client
                
                # Attempt repair
                repair_result = await strategy.repair(
                    raw_output=raw_output,
                    error_message=error_message,
                    schema=self.schema
                )
                
                if repair_result.success and repair_result.data:
                    # Validate repaired data
                    is_valid, validation_error = await self._validate_data(repair_result.data)
                    
                    if is_valid:
                        # Successful repair
                        self.circuit_breaker.record_success()
                        self.observability.increment(f'repair.{self.agent_name}.{strategy.name}.success')
                        return self._create_success_response(
                            repair_result.data, 
                            repair_result.strategy_used,
                            start_time,
                            repair_result.confidence
                        )
                    else:
                        # Repair didn't solve validation issue
                        self.observability.increment(f'repair.{self.agent_name}.{strategy.name}.invalid')
                        continue
                else:
                    # Repair failed
                    self.observability.increment(f'repair.{self.agent_name}.{strategy.name}.failed')
                    continue
                    
            except Exception as e:
                # Strategy failed with exception
                self.observability.increment(f'repair.{self.agent_name}.{strategy.name}.error')
                print(f"[ValidationWrapper] Repair strategy {strategy.name} failed: {e}")
                continue
        
        # All repair attempts failed
        self.circuit_breaker.record_failure(f"All repairs failed: {error_message}")
        return self._create_error_response(f"Validation failed after all repairs: {error_message}", start_time)

    async def _extract_json_with_timing(self, response: str) -> Dict:
        """Extract JSON with observability timing"""
        start = time.time()
        
        try:
            if self.legacy_mode:
                data = self._extract_json_legacy(response)
            else:
                data = self._extract_json_enhanced(response)
            
            self.observability.increment(f'json_extraction.{self.agent_name}.success')
            return data
            
        except Exception as e:
            self.observability.increment(f'json_extraction.{self.agent_name}.failed')
            raise
        finally:
            self.observability.record_time(f'json_extraction.{self.agent_name}.latency_ms', (time.time() - start) * 1000)

    def _extract_json_legacy(self, response: str) -> Dict:
        """Legacy JSON extraction logic"""
        start = response.find('{')
        end = response.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        
        raw = response[start:end]
        # Apply basic repairs before parsing
        raw = self._repair_malformed_json_legacy(raw)
        return json.loads(raw)

    def _extract_json_enhanced(self, response: str) -> Dict:
        """Enhanced JSON extraction with better error handling"""
        # Try multiple JSON extraction approaches
        candidates = []
        
        # Method 1: Find outermost braces
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            candidates.append(response[start:end])
        
        # Method 2: Look for JSON code blocks
        import re
        code_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        candidates.extend(code_blocks)
        
        # Method 3: Look for structured JSON patterns
        json_patterns = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        candidates.extend(json_patterns)
        
        # Try parsing each candidate
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        
        # If no valid JSON found, raise error
        raise ValueError(f"No valid JSON found in response: {response[:200]}...")

    async def _validate_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate data against schema with timing"""
        start = time.time()
        
        try:
            if self.schema:
                # Pydantic validation
                try:
                    self.schema.model_validate(data)
                    return True, ""
                except PydanticValidationError as e:
                    return False, str(e)
            elif self.schema_name and self.legacy_mode:
                # Legacy schema validation
                valid, error_msg, _ = validator.validate(self.schema_name, data)
                return valid, error_msg or ""
            else:
                # No schema - just check it's a dict
                return isinstance(data, dict) and len(data) > 0, "Invalid data structure"
                
        finally:
            self.observability.record_time(f'validation.{self.agent_name}.latency_ms', (time.time() - start) * 1000)

    def _create_success_response(self, data: Dict, method: str, start_time: float, confidence: float = 0.95) -> Dict:
        """Create successful validation response"""
        processing_time = int((time.time() - start_time) * 1000)
        
        result = data.copy()
        result.update({
            "processing_method": method,
            "confidence": confidence,
            "processing_time_ms": processing_time
        })
        
        return result

    def _create_bypass_response(self, raw_output: str, reason: str) -> Dict:
        """Create response when validation is bypassed"""
        # Try to extract any valid content
        try:
            data = json.loads(raw_output) if raw_output.strip().startswith('{') else {}
        except:
            data = {"output": raw_output[:500] if raw_output else "No output provided"}
        
        data.update({
            "processing_method": f"bypass_{reason}",
            "confidence": 0.1,
            "processing_time_ms": 0
        })
        
        self.observability.increment(f'validation.{self.agent_name}.bypass.{reason}')
        return data

    def _create_error_response(self, error: str, start_time: float) -> Dict:
        """Create error response as fallback"""
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "output": f"Validation failed: {error}",
            "sources": [],
            "processing_method": "error_fallback",
            "confidence": 0.0,
            "processing_time_ms": processing_time
        }

    def _repair_malformed_json_legacy(self, malformed_json: str) -> str:
        """Legacy repair patterns for backward compatibility"""
        fixed = malformed_json
        # Apply existing patterns
        fixed = fixed.replace('```json', '').replace('```', '')
        fixed = re.sub(r'"schema_v\s*\n\s*on"', '"schema_version"', fixed)
        fixed = fixed.replace('"schema_tag":', '"schema_version":')
        fixed = re.sub(r'}\s*\n\s*{', '},\n    {', fixed)
        fixed = re.sub(r'(?<!")https?://[^\s,}\]]+', lambda m: f'"{m.group(0)}"', fixed)
        fixed = re.sub(r'--\([^)]*\)', '', fixed)
        return fixed

    def get_status(self) -> Dict:
        """Get current validation wrapper status"""
        return {
            "agent_name": self.agent_name,
            "enabled": self.config.enabled,
            "schema": self.schema.__name__ if self.schema else self.schema_name,
            "legacy_mode": self.legacy_mode,
            "circuit_breaker": self.circuit_breaker.get_status(),
            "repair_strategies": [s.name for s in self.repair_strategies]
        }


# Legacy compatibility class
class LegacyValidationWrapper(ValidationWrapper):
    """Backward compatibility wrapper for existing code"""
    
    def __init__(
        self,
        schema_name: str,
        agent_name: str,
        call_with_functions: Callable[..., Awaitable[str]],
        observability: ObservabilityHandler = None,
    ):
        super().__init__(
            agent_name=agent_name,
            schema_name=schema_name,
            call_with_functions=call_with_functions,
            observability=observability
        )
