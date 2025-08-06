#!/usr/bin/env python3
"""
Model Role Registry for 4-Model Architecture

This module implements role-based model validation for the agents framework,
ensuring each model is capable of handling its assigned role (PLANNER, TOOL_CALLING, 
SUMMARISER, WRITER). It uses HuggingFace model tags for capability discovery while
supporting Ollama-hosted local models.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse
import aiohttp
import os

logger = logging.getLogger(__name__)


class ModelRole(Enum):
    """Defines the 5 model roles in the architecture."""
    PLANNER = "planner"
    TOOL_CALLING = "tool_calling" 
    SUMMARISER = "summariser"
    WRITER = "writer"
    KNOWLEDGE_GAP = "knowledge_gap"


@dataclass
class RoleSpecification:
    """Specification for what a model role requires."""
    role: ModelRole
    required_capabilities: Set[str] = field(default_factory=set)
    preferred_tags: Set[str] = field(default_factory=set)
    min_context_length: Optional[int] = None
    supports_function_calling: bool = False
    description: str = ""


@dataclass
class ModelInfo:
    """Information about a model's capabilities."""
    model_id: str
    provider: str  # 'local' for Ollama, 'openai' etc.
    hf_model_id: Optional[str] = None  # HuggingFace model ID if different
    tags: Set[str] = field(default_factory=set)
    context_length: Optional[int] = None
    supports_function_calling: bool = False
    validated_roles: Set[ModelRole] = field(default_factory=set)
    last_validated: Optional[float] = None


class ModelRoleRegistry:
    """Registry for validating model-role assignments."""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self._model_cache: Dict[str, ModelInfo] = {}
        self._hf_cache: Dict[str, dict] = {}
        self._role_specs = self._initialize_role_specs()
        
    def _initialize_role_specs(self) -> Dict[ModelRole, RoleSpecification]:
        """Initialize the role specifications based on validated architecture."""
        return {
            ModelRole.PLANNER: RoleSpecification(
                role=ModelRole.PLANNER,
                required_capabilities={'text-generation', 'reasoning'},
                preferred_tags={'planning', 'reasoning', 'instruction-following'},
                min_context_length=4096,
                supports_function_calling=False,
                description="Plans research tasks and breaks down complex queries"
            ),
            
            ModelRole.TOOL_CALLING: RoleSpecification(
                role=ModelRole.TOOL_CALLING,
                required_capabilities={'text-generation', 'function-calling'},
                preferred_tags={'function-calling', 'tool-use', 'agents'},
                min_context_length=4096,
                supports_function_calling=True,
                description="Executes function calls and tool interactions (CRITICAL: Must produce ResponseFunctionToolCall objects)"
            ),
            
            ModelRole.SUMMARISER: RoleSpecification(
                role=ModelRole.SUMMARISER,
                required_capabilities={'text-generation', 'summarization'},
                preferred_tags={'summarization', 'text-classification', 'information-extraction'},
                min_context_length=8192,  # Needs longer context for large documents
                supports_function_calling=False,
                description="Summarizes and extracts key information from documents"
            ),
            
            ModelRole.WRITER: RoleSpecification(
                role=ModelRole.WRITER,
                required_capabilities={'text-generation'},
                preferred_tags={'text-generation', 'creative-writing', 'instruction-following'},
                min_context_length=4096,
                supports_function_calling=False,
                description="Generates final research reports and documentation"
            ),
            
            ModelRole.KNOWLEDGE_GAP: RoleSpecification(
                role=ModelRole.KNOWLEDGE_GAP,
                required_capabilities={'text-generation', 'reasoning', 'analysis'},
                preferred_tags={'reasoning', 'analysis', 'instruction-following', 'evaluation'},
                min_context_length=8192,  # Needs longer context for research history analysis
                supports_function_calling=False,
                description="Analyzes research progress and identifies knowledge gaps"
            )
        }
    
    def get_role_specification(self, role: ModelRole) -> RoleSpecification:
        """Get the specification for a given role."""
        return self._role_specs[role]
    
    async def get_ollama_models(self) -> List[str]:
        """Fetch list of models available in Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['name'] for model in data.get('models', [])]
                    else:
                        logger.warning(f"Failed to fetch Ollama models: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.warning(f"Could not connect to Ollama at {self.ollama_base_url}: {e}")
            return []
    
    def _extract_hf_model_id(self, model_id: str) -> Optional[str]:
        """Extract HuggingFace model ID from various formats."""
        # Handle common Ollama model formats that map to HF models
        if model_id.startswith('hf.co/'):
            # Format: hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M
            parts = model_id.replace('hf.co/', '').split(':')
            base_model = parts[0]
            # Convert GGUF naming back to original HF format
            if '_' in base_model and 'GGUF' in base_model:
                # tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF -> Salesforce/Llama-xLAM-2-8b-fc-r
                parts = base_model.split('/')
                if len(parts) >= 2:
                    model_name = parts[1].replace('_', '/').replace('-GGUF', '')
                    return model_name
            return base_model
        
        # Handle direct HF model IDs
        if '/' in model_id and not model_id.startswith('http'):
            return model_id
            
        # Known mappings for common local models
        known_mappings = {
            'hermes3:8b': 'NousResearch/Hermes-3-Llama-3.1-8B',
            'qwen2.5-coder:latest': 'Qwen/Qwen2.5-Coder-7B-Instruct',
            'llama3.2:latest': 'meta-llama/Llama-3.2-3B-Instruct',
        }
        
        return known_mappings.get(model_id)
    
    async def fetch_hf_model_info(self, hf_model_id: str) -> Optional[dict]:
        """Fetch model information from HuggingFace."""
        if hf_model_id in self._hf_cache:
            return self._hf_cache[hf_model_id]
        
        try:
            url = f"https://huggingface.co/api/models/{hf_model_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._hf_cache[hf_model_id] = data
                        return data
                    else:
                        logger.warning(f"Failed to fetch HF model info for {hf_model_id}: HTTP {response.status}")
        except Exception as e:
            logger.warning(f"Error fetching HF model info for {hf_model_id}: {e}")
        
        return None
    
    def _extract_capabilities_from_tags(self, hf_data: dict) -> Set[str]:
        """Extract capabilities from HuggingFace model tags."""
        capabilities = set()
        
        # Get pipeline tag (primary capability)
        pipeline_tag = hf_data.get('pipeline_tag')
        if pipeline_tag:
            capabilities.add(pipeline_tag)
        
        # Get library tags
        library_name = hf_data.get('library_name')
        if library_name:
            capabilities.add(library_name)
        
        # Get model tags
        tags = hf_data.get('tags', [])
        for tag in tags:
            if isinstance(tag, str):
                capabilities.add(tag.lower())
        
        # Infer function calling capability from model name/tags
        model_name = hf_data.get('modelId', '').lower()
        function_calling_indicators = [
            'function', 'tool', 'xlam', 'gorilla', 'toolformer', 'agent'
        ]
        
        if any(indicator in model_name for indicator in function_calling_indicators):
            capabilities.add('function-calling')
        
        if any(indicator in str(tags).lower() for indicator in function_calling_indicators):
            capabilities.add('function-calling')
        
        return capabilities
    
    async def get_model_info(self, model_id: str, provider: str = 'local') -> ModelInfo:
        """Get comprehensive model information."""
        cache_key = f"{provider}:{model_id}"
        
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        
        # Create base model info
        model_info = ModelInfo(
            model_id=model_id,
            provider=provider,
            hf_model_id=self._extract_hf_model_id(model_id)
        )
        
        # Fetch HuggingFace information if available
        if model_info.hf_model_id:
            hf_data = await self.fetch_hf_model_info(model_info.hf_model_id)
            if hf_data:
                model_info.tags = self._extract_capabilities_from_tags(hf_data)
                model_info.supports_function_calling = 'function-calling' in model_info.tags
                
                # Try to extract context length from config
                config = hf_data.get('config', {})
                model_info.context_length = (
                    config.get('max_position_embeddings') or
                    config.get('max_sequence_length') or
                    config.get('context_length')
                )
        
        # Apply known model characteristics
        self._apply_known_model_characteristics(model_info)
        
        # Cache and return
        self._model_cache[cache_key] = model_info
        return model_info
    
    def _apply_known_model_characteristics(self, model_info: ModelInfo):
        """Apply known characteristics for specific models."""
        model_id_lower = model_info.model_id.lower()
        
        # Tool calling models (validated to work)
        if 'xlam' in model_id_lower or 'salesforce_llama-xlam' in model_id_lower:
            model_info.supports_function_calling = True
            model_info.tags.update(['function-calling', 'tool-use', 'agents'])
            model_info.validated_roles.add(ModelRole.TOOL_CALLING)
        
        # Reasoning/planning models
        if any(x in model_id_lower for x in ['hermes', 'qwen', 'llama', 'phi3']):
            model_info.tags.update(['text-generation', 'reasoning', 'instruction-following'])
            model_info.validated_roles.update([ModelRole.PLANNER, ModelRole.WRITER])
        
        # Analysis-capable models (for KNOWLEDGE_GAP role)
        if any(x in model_id_lower for x in ['hermes', 'qwen', 'llama', 'phi3']):
            model_info.tags.update(['analysis', 'evaluation', 'critical-thinking'])
            model_info.validated_roles.add(ModelRole.KNOWLEDGE_GAP)
        
        # Summarization-capable models
        if any(x in model_id_lower for x in ['qwen', 'llama', 'hermes', 'phi3']):
            model_info.tags.add('summarization')
            model_info.validated_roles.add(ModelRole.SUMMARISER)
    
    def validate_model_for_role(self, model_info: ModelInfo, role: ModelRole) -> tuple[bool, List[str]]:
        """Validate if a model can handle a specific role."""
        spec = self._role_specs[role]
        issues = []
        
        # Check required capabilities
        missing_capabilities = spec.required_capabilities - model_info.tags
        if missing_capabilities:
            issues.append(f"Missing required capabilities: {missing_capabilities}")
        
        # Check function calling requirement
        if spec.supports_function_calling and not model_info.supports_function_calling:
            issues.append("Model does not support function calling (required for this role)")
        
        # Check context length
        if spec.min_context_length and model_info.context_length:
            if model_info.context_length < spec.min_context_length:
                issues.append(f"Context length {model_info.context_length} < required {spec.min_context_length}")
        
        # Special validation for TOOL_CALLING role (critical for pipeline)
        if role == ModelRole.TOOL_CALLING:
            if not model_info.supports_function_calling:
                issues.append("CRITICAL: Tool calling models must support function calling to prevent pipeline failures")
            
            # Check for validated models
            if 'xlam' not in model_info.model_id.lower():
                issues.append("WARNING: Model not validated for tool calling. Consider using Salesforce_Llama-xLAM-2-8b-fc-r-GGUF")
        
        return len(issues) == 0, issues
    
    async def validate_5_model_config(self, config_dict: Dict[str, str]) -> Dict[ModelRole, tuple[bool, List[str]]]:
        """Validate a complete 5-model configuration."""
        expected_roles = {
            'PLANNER_MODEL': ModelRole.PLANNER,
            'TOOL_CALLING_MODEL': ModelRole.TOOL_CALLING,
            'SUMMARISER_MODEL': ModelRole.SUMMARISER,
            'WRITER_MODEL': ModelRole.WRITER,
            'KNOWLEDGE_GAP_MODEL': ModelRole.KNOWLEDGE_GAP
        }
        
        results = {}
        
        for config_key, role in expected_roles.items():
            model_id = config_dict.get(config_key)
            if not model_id:
                results[role] = (False, [f"Missing configuration: {config_key}"])
                continue
            
            provider = config_dict.get(f"{config_key}_PROVIDER", "local")
            model_info = await self.get_model_info(model_id, provider)
            results[role] = self.validate_model_for_role(model_info, role)
        
        return results
    
    async def validate_4_model_config(self, config_dict: Dict[str, str]) -> Dict[ModelRole, tuple[bool, List[str]]]:
        """Validate a complete 4-model configuration (legacy compatibility)."""
        expected_roles = {
            'PLANNER_MODEL': ModelRole.PLANNER,
            'TOOL_CALLING_MODEL': ModelRole.TOOL_CALLING,
            'SUMMARISER_MODEL': ModelRole.SUMMARISER,
            'WRITER_MODEL': ModelRole.WRITER
        }
        
        results = {}
        
        for config_key, role in expected_roles.items():
            model_id = config_dict.get(config_key)
            if not model_id:
                results[role] = (False, [f"Missing configuration: {config_key}"])
                continue
            
            provider = config_dict.get(f"{config_key}_PROVIDER", "local")
            model_info = await self.get_model_info(model_id, provider)
            results[role] = self.validate_model_for_role(model_info, role)
        
        return results
    
    async def suggest_models_for_role(self, role: ModelRole, available_models: List[str]) -> List[str]:
        """Suggest suitable models for a given role from available models."""
        suggestions = []
        
        for model_id in available_models:
            model_info = await self.get_model_info(model_id, 'local')
            is_valid, _ = self.validate_model_for_role(model_info, role)
            
            if is_valid:
                suggestions.append(model_id)
        
        return suggestions
    
    def get_validation_summary(self, validation_results: Dict[ModelRole, tuple[bool, List[str]]]) -> str:
        """Generate a human-readable validation summary."""
        lines = ["4-Model Architecture Validation Summary:", "=" * 45]
        
        for role, (is_valid, issues) in validation_results.items():
            status = "[VALID]" if is_valid else "[INVALID]"
            lines.append(f"{role.value.upper()}: {status}")
            
            if issues:
                for issue in issues:
                    lines.append(f"  - {issue}")
            lines.append("")
        
        # Overall status
        all_valid = all(is_valid for is_valid, _ in validation_results.values())
        overall = "[SUCCESS] All roles properly configured" if all_valid else "[ISSUES] Configuration issues detected"
        lines.append(f"OVERALL: {overall}")
        
        return "\n".join(lines)


# Global registry instance
_registry = None

def get_model_registry() -> ModelRoleRegistry:
    """Get the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRoleRegistry()
    return _registry