#!/usr/bin/env python3
"""
Runtime Assertion Framework for 4-Model Architecture

This module provides runtime validation and assertion capabilities to ensure
model-role compatibility before agent execution, preventing the tool execution
pipeline failures discovered during HYBRID-05 investigation.

Key Features:
- Pre-execution model-role validation
- Fail-fast error reporting with actionable messages
- Performance-optimized assertions (<100ms overhead)
- Integration with ResearchRunner workflow
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from contextlib import asynccontextmanager

from .model_role_registry import ModelRole, ModelRoleRegistry, get_model_registry

logger = logging.getLogger(__name__)


class AssertionSeverity(Enum):
    """Severity levels for runtime assertions."""
    CRITICAL = "critical"  # Must pass or execution fails
    WARNING = "warning"   # Issues logged but execution continues
    INFO = "info"        # Informational only


@dataclass
class AssertionResult:
    """Result of a runtime assertion check."""
    passed: bool
    severity: AssertionSeverity
    message: str
    execution_time_ms: float
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class ModelRoleAssertion:
    """Configuration for a model-role assertion."""
    role: ModelRole
    model_id: str
    provider: str
    required: bool = True  # If True, failure blocks execution
    
    @property
    def severity(self) -> AssertionSeverity:
        return AssertionSeverity.CRITICAL if self.required else AssertionSeverity.WARNING


class RuntimeAssertionError(Exception):
    """Exception raised when critical runtime assertions fail."""
    
    def __init__(self, message: str, failed_assertions: List[AssertionResult] = None):
        super().__init__(message)
        self.failed_assertions = failed_assertions or []
        
    def get_actionable_message(self) -> str:
        """Generate an actionable error message for users."""
        lines = [
            "CRITICAL: Model-Role Validation Failed",
            "=" * 50,
            "",
            "The 4-model architecture validation detected configuration issues",
            "that would cause tool execution pipeline failures.",
            "",
            "Failed Assertions:"
        ]
        
        for assertion in self.failed_assertions:
            if assertion.severity == AssertionSeverity.CRITICAL:
                lines.append(f"  [CRITICAL]: {assertion.message}")
                for suggestion in assertion.suggestions:
                    lines.append(f"    Suggestion: {suggestion}")
                lines.append("")
        
        lines.extend([
            "Resolution Steps:",
            "1. Update your model configuration to use validated models",
            "2. For TOOL_CALLING role, use: hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            "3. Run 'python demo_model_role_registry.py' to validate your configuration",
            "4. Check the HYBRID-08 documentation for complete setup guide",
            "",
            "This validation prevents the pipeline failures discovered in HYBRID-05:",
            "  [FAILED] Wrong Model -> ResponseOutputMessage -> functions count: 0 -> No Tools",
            "  [SUCCESS] Right Model -> ResponseFunctionToolCall -> functions count: 1 -> Tools Execute"
        ])
        
        return "\n".join(lines)


class RuntimeAssertionFramework:
    """Framework for running model-role assertions before agent execution."""
    
    def __init__(self, registry: Optional[ModelRoleRegistry] = None):
        self.registry = registry or get_model_registry()
        self._assertion_cache: Dict[str, AssertionResult] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
        self._enabled = True
        
    def enable(self):
        """Enable runtime assertions."""
        self._enabled = True
        logger.info("Runtime assertions enabled")
    
    def disable(self):
        """Disable runtime assertions (for development/testing)."""
        self._enabled = False
        logger.warning("Runtime assertions disabled")
    
    def _get_cache_key(self, assertion: ModelRoleAssertion) -> str:
        """Generate cache key for assertion result."""
        return f"{assertion.provider}:{assertion.model_id}:{assertion.role.value}"
    
    def _is_cache_valid(self, assertion_result: AssertionResult) -> bool:
        """Check if cached assertion result is still valid."""
        return (time.time() - assertion_result.execution_time_ms / 1000) < self._cache_ttl_seconds
    
    async def validate_single_assertion(self, assertion: ModelRoleAssertion) -> AssertionResult:
        """Validate a single model-role assertion."""
        start_time = time.perf_counter()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(assertion)
            if cache_key in self._assertion_cache:
                cached_result = self._assertion_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"Using cached assertion result for {cache_key}")
                    return cached_result
            
            # Get model info
            model_info = await self.registry.get_model_info(assertion.model_id, assertion.provider)
            
            # Validate model for role
            is_valid, issues = self.registry.validate_model_for_role(model_info, assertion.role)
            
            # Determine result
            if is_valid:
                result = AssertionResult(
                    passed=True,
                    severity=assertion.severity,
                    message=f"{assertion.role.value.upper()} model '{assertion.model_id}' is valid",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000
                )
            else:
                # Generate suggestions based on issues
                suggestions = []
                if assertion.role == ModelRole.TOOL_CALLING:
                    suggestions.append("Use hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M for reliable tool execution")
                    suggestions.append("This model is validated to produce ResponseFunctionToolCall objects")
                
                if "function calling" in " ".join(issues).lower():
                    suggestions.append("Choose a model with 'function-calling' tag from HuggingFace")
                
                if "context length" in " ".join(issues).lower():
                    suggestions.append("Use a model with larger context window for this role")
                
                result = AssertionResult(
                    passed=False,
                    severity=assertion.severity,
                    message=f"{assertion.role.value.upper()} model '{assertion.model_id}' validation failed: {'; '.join(issues)}",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    suggestions=suggestions
                )
            
            # Cache result
            self._assertion_cache[cache_key] = result
            return result
            
        except Exception as e:
            # Handle validation errors gracefully
            result = AssertionResult(
                passed=False,
                severity=AssertionSeverity.CRITICAL,
                message=f"Failed to validate {assertion.role.value.upper()} model '{assertion.model_id}': {e}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                suggestions=["Check model availability and network connectivity", "Verify model ID format"]
            )
            return result
    
    async def validate_assertions(self, assertions: List[ModelRoleAssertion]) -> List[AssertionResult]:
        """Validate multiple assertions in parallel for performance."""
        if not self._enabled:
            logger.debug("Runtime assertions disabled, skipping validation")
            return []
        
        if not assertions:
            return []
        
        start_time = time.perf_counter()
        
        # Run all validations in parallel
        tasks = [self.validate_single_assertion(assertion) for assertion in assertions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed assertion results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AssertionResult(
                    passed=False,
                    severity=AssertionSeverity.CRITICAL,
                    message=f"Assertion validation failed: {result}",
                    execution_time_ms=0,
                    suggestions=["Check system configuration and dependencies"]
                ))
            else:
                processed_results.append(result)
        
        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"Validated {len(assertions)} assertions in {total_time:.1f}ms")
        
        return processed_results
    
    def check_assertion_results(self, results: List[AssertionResult]) -> None:
        """Check assertion results and raise exception if critical failures exist."""
        if not results:
            return
        
        failed_critical = [r for r in results if not r.passed and r.severity == AssertionSeverity.CRITICAL]
        failed_warnings = [r for r in results if not r.passed and r.severity == AssertionSeverity.WARNING]
        
        # Log warnings
        for warning in failed_warnings:
            logger.warning(f"Model validation warning: {warning.message}")
            for suggestion in warning.suggestions:
                logger.warning(f"  Suggestion: {suggestion}")
        
        # Raise exception for critical failures
        if failed_critical:
            error_message = f"Critical model validation failures detected ({len(failed_critical)} issues)"
            raise RuntimeAssertionError(error_message, failed_critical)
    
    async def assert_model_role_compatibility(self, model_id: str, provider: str, role: ModelRole, 
                                            required: bool = True) -> AssertionResult:
        """Assert that a specific model is compatible with a role."""
        assertion = ModelRoleAssertion(
            role=role,
            model_id=model_id,
            provider=provider,
            required=required
        )
        
        result = await self.validate_single_assertion(assertion)
        
        if required and not result.passed:
            raise RuntimeAssertionError(
                f"Critical assertion failed: {result.message}",
                [result]
            )
        
        return result
    
    @asynccontextmanager
    async def assert_agent_model_compatibility(self, agent_model_id: str, agent_provider: str, 
                                             expected_role: ModelRole):
        """Context manager for asserting agent model compatibility before execution."""
        start_time = time.perf_counter()
        
        try:
            # Pre-execution assertion
            logger.info(f"Validating {expected_role.value} model compatibility for agent execution")
            
            result = await self.assert_model_role_compatibility(
                model_id=agent_model_id,
                provider=agent_provider,
                role=expected_role,
                required=True
            )
            
            if result.passed:
                logger.info(f"✅ Model validation passed: {result.message}")
            
            yield result
            
        except RuntimeAssertionError as e:
            logger.error(f"❌ Model validation failed: {e}")
            logger.error("\n" + e.get_actionable_message())
            raise
        
        finally:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Model compatibility assertion completed in {total_time:.1f}ms")
    
    def get_assertion_stats(self) -> Dict[str, Any]:
        """Get statistics about assertion performance and results."""
        total_assertions = len(self._assertion_cache)
        passed_assertions = sum(1 for r in self._assertion_cache.values() if r.passed)
        
        avg_execution_time = 0
        if total_assertions > 0:
            avg_execution_time = sum(r.execution_time_ms for r in self._assertion_cache.values()) / total_assertions
        
        return {
            "total_assertions": total_assertions,
            "passed_assertions": passed_assertions,
            "failed_assertions": total_assertions - passed_assertions,
            "cache_hit_rate": total_assertions,
            "avg_execution_time_ms": avg_execution_time,
            "enabled": self._enabled
        }


# Global assertion framework instance
_assertion_framework = None

def get_assertion_framework() -> RuntimeAssertionFramework:
    """Get the global assertion framework instance."""
    global _assertion_framework
    if _assertion_framework is None:
        _assertion_framework = RuntimeAssertionFramework()
    return _assertion_framework