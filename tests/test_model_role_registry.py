#!/usr/bin/env python3
"""
Unit tests for Model Role Registry functionality.

Tests the role validation system, HuggingFace integration, and Ollama model support.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from deep_researcher.agents.utils.model_role_registry import (
    ModelRole,
    ModelRoleRegistry,
    RoleSpecification,
    ModelInfo,
    get_model_registry
)


class TestModelRoleRegistry:
    """Test suite for ModelRoleRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ModelRoleRegistry("http://localhost:11434")
    
    def test_role_specifications_initialization(self):
        """Test that role specifications are properly initialized."""
        specs = self.registry._role_specs
        
        # All 4 roles should be defined
        assert len(specs) == 4
        assert ModelRole.PLANNER in specs
        assert ModelRole.TOOL_CALLING in specs
        assert ModelRole.SUMMARISER in specs
        assert ModelRole.WRITER in specs
        
        # Tool calling role should require function calling
        tool_spec = specs[ModelRole.TOOL_CALLING]
        assert tool_spec.supports_function_calling is True
        assert 'function-calling' in tool_spec.required_capabilities
        
        # Other roles should not require function calling
        assert specs[ModelRole.PLANNER].supports_function_calling is False
        assert specs[ModelRole.SUMMARISER].supports_function_calling is False
        assert specs[ModelRole.WRITER].supports_function_calling is False
    
    def test_extract_hf_model_id(self):
        """Test HuggingFace model ID extraction from various formats."""
        test_cases = [
            # Ollama HF format
            ("hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M", "Salesforce/Llama-xLAM-2-8b-fc-r"),
            # Direct HF format
            ("microsoft/DialoGPT-medium", "microsoft/DialoGPT-medium"),
            # Known local model mappings
            ("hermes3:8b", "NousResearch/Hermes-3-Llama-3.1-8B"),
            ("qwen2.5-coder:latest", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            # Unknown model
            ("unknown-model:latest", None),
        ]
        
        for input_model, expected_hf_id in test_cases:
            result = self.registry._extract_hf_model_id(input_model)
            assert result == expected_hf_id, f"Failed for {input_model}: got {result}, expected {expected_hf_id}"
    
    def test_extract_capabilities_from_tags(self):
        """Test capability extraction from HuggingFace model data."""
        # Mock HF data for a function calling model
        hf_data_function_calling = {
            'modelId': 'Salesforce/Llama-xLAM-2-8b-fc-r',
            'pipeline_tag': 'text-generation',
            'library_name': 'transformers',
            'tags': ['function-calling', 'tool-use', 'agents']
        }
        
        capabilities = self.registry._extract_capabilities_from_tags(hf_data_function_calling)
        
        assert 'text-generation' in capabilities
        assert 'transformers' in capabilities
        assert 'function-calling' in capabilities
        assert 'tool-use' in capabilities
        assert 'agents' in capabilities
    
    def test_apply_known_model_characteristics(self):
        """Test application of known model characteristics."""
        # Test function calling model
        xlam_model = ModelInfo(
            model_id="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            provider="local"
        )
        self.registry._apply_known_model_characteristics(xlam_model)
        
        assert xlam_model.supports_function_calling is True
        assert 'function-calling' in xlam_model.tags
        assert ModelRole.TOOL_CALLING in xlam_model.validated_roles
        
        # Test general purpose model
        hermes_model = ModelInfo(
            model_id="hermes3:8b",
            provider="local"
        )
        self.registry._apply_known_model_characteristics(hermes_model)
        
        assert 'text-generation' in hermes_model.tags
        assert 'reasoning' in hermes_model.tags
        assert ModelRole.PLANNER in hermes_model.validated_roles
        assert ModelRole.WRITER in hermes_model.validated_roles
        assert ModelRole.SUMMARISER in hermes_model.validated_roles
    
    def test_validate_model_for_role_success(self):
        """Test successful model validation for roles."""
        # Create a model suitable for tool calling
        tool_model = ModelInfo(
            model_id="xlam-model",
            provider="local",
            tags={'text-generation', 'function-calling'},
            supports_function_calling=True,
            context_length=8192
        )
        
        is_valid, issues = self.registry.validate_model_for_role(tool_model, ModelRole.TOOL_CALLING)
        assert is_valid is True
        assert len(issues) == 0
        
        # Create a model suitable for planning
        planner_model = ModelInfo(
            model_id="hermes-model",
            provider="local", 
            tags={'text-generation', 'reasoning'},
            supports_function_calling=False,
            context_length=8192
        )
        
        is_valid, issues = self.registry.validate_model_for_role(planner_model, ModelRole.PLANNER)
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_model_for_role_failure(self):
        """Test model validation failures."""
        # Model without function calling for tool role
        bad_tool_model = ModelInfo(
            model_id="basic-model",
            provider="local",
            tags={'text-generation'},
            supports_function_calling=False
        )
        
        is_valid, issues = self.registry.validate_model_for_role(bad_tool_model, ModelRole.TOOL_CALLING)
        assert is_valid is False
        assert any("function calling" in issue.lower() for issue in issues)
        
        # Model with insufficient context for summarization
        small_context_model = ModelInfo(
            model_id="small-model",
            provider="local",
            tags={'text-generation', 'summarization'},
            context_length=2048  # Less than required 8192
        )
        
        is_valid, issues = self.registry.validate_model_for_role(small_context_model, ModelRole.SUMMARISER)
        assert is_valid is False
        assert any("context length" in issue.lower() for issue in issues)
    
    @patch('aiohttp.ClientSession.get')
    async def test_fetch_hf_model_info(self, mock_get):
        """Test HuggingFace model info fetching."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'modelId': 'test/model',
            'pipeline_tag': 'text-generation',
            'tags': ['instruction-following']
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.registry.fetch_hf_model_info('test/model')
        
        assert result is not None
        assert result['modelId'] == 'test/model'
        assert result['pipeline_tag'] == 'text-generation'
        
        # Should be cached
        assert 'test/model' in self.registry._hf_cache
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_ollama_models(self, mock_get):
        """Test Ollama model list fetching."""
        # Mock successful Ollama response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'hermes3:8b'},
                {'name': 'qwen2.5-coder:latest'},
                {'name': 'llama3.2:latest'}
            ]
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        models = await self.registry.get_ollama_models()
        
        assert len(models) == 3
        assert 'hermes3:8b' in models
        assert 'qwen2.5-coder:latest' in models
        assert 'llama3.2:latest' in models
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_model_info_with_hf_data(self, mock_get):
        """Test getting comprehensive model info with HF data."""
        # Mock HF API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'modelId': 'NousResearch/Hermes-3-Llama-3.1-8B',
            'pipeline_tag': 'text-generation',
            'library_name': 'transformers',
            'tags': ['instruction-following', 'reasoning'],
            'config': {
                'max_position_embeddings': 8192
            }
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        model_info = await self.registry.get_model_info('hermes3:8b', 'local')
        
        assert model_info.model_id == 'hermes3:8b'
        assert model_info.provider == 'local'
        assert model_info.hf_model_id == 'NousResearch/Hermes-3-Llama-3.1-8B'
        assert 'text-generation' in model_info.tags
        assert 'reasoning' in model_info.tags
        assert model_info.context_length == 8192
    
    async def test_validate_4_model_config_complete(self):
        """Test validation of complete 4-model configuration."""
        config = {
            'PLANNER_MODEL': 'hermes3:8b',
            'PLANNER_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest',
            'WRITER_MODEL_PROVIDER': 'local'
        }
        
        with patch.object(self.registry, 'get_model_info') as mock_get_info:
            # Mock different model infos for each role
            mock_get_info.side_effect = [
                ModelInfo('hermes3:8b', 'local', tags={'text-generation', 'reasoning'}, context_length=8192),
                ModelInfo('xlam-model', 'local', tags={'text-generation', 'function-calling'}, supports_function_calling=True, context_length=8192),
                ModelInfo('qwen-model', 'local', tags={'text-generation', 'summarization'}, context_length=16384),
                ModelInfo('llama-model', 'local', tags={'text-generation'}, context_length=8192)
            ]
            
            results = await self.registry.validate_4_model_config(config)
            
            assert len(results) == 4
            assert ModelRole.PLANNER in results
            assert ModelRole.TOOL_CALLING in results
            assert ModelRole.SUMMARISER in results 
            assert ModelRole.WRITER in results
    
    async def test_validate_4_model_config_missing(self):
        """Test validation with missing model configuration."""
        incomplete_config = {
            'PLANNER_MODEL': 'hermes3:8b',
            # Missing TOOL_CALLING_MODEL
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        results = await self.registry.validate_4_model_config(incomplete_config)
        
        # Should have validation failure for missing TOOL_CALLING_MODEL
        tool_result = results[ModelRole.TOOL_CALLING]
        assert tool_result[0] is False  # is_valid = False
        assert any("Missing configuration" in issue for issue in tool_result[1])
    
    def test_get_validation_summary(self):
        """Test validation summary generation."""
        validation_results = {
            ModelRole.PLANNER: (True, []),
            ModelRole.TOOL_CALLING: (True, []),
            ModelRole.SUMMARISER: (False, ["Missing required capabilities"]),
            ModelRole.WRITER: (True, [])
        }
        
        summary = self.registry.get_validation_summary(validation_results)
        
        assert "4-Model Architecture Validation Summary" in summary
        assert "PLANNER: [VALID]" in summary
        assert "TOOL_CALLING: [VALID]" in summary  
        assert "SUMMARISER: [INVALID]" in summary
        assert "WRITER: [VALID]" in summary
        assert "[ISSUES] Configuration issues detected" in summary
    
    def test_global_registry_singleton(self):
        """Test that global registry returns same instance."""
        registry1 = get_model_registry()
        registry2 = get_model_registry()
        
        assert registry1 is registry2


class TestIntegration:
    """Integration tests for model role registry."""
    
    @pytest.mark.asyncio
    async def test_real_model_validation_workflow(self):
        """Test the complete workflow with realistic model configurations."""
        registry = ModelRoleRegistry()
        
        # Test with the validated tool calling model
        tool_model_info = await registry.get_model_info(
            'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'local'
        )
        
        # Should be valid for tool calling
        is_valid, issues = registry.validate_model_for_role(tool_model_info, ModelRole.TOOL_CALLING)
        
        # This should pass based on our known model characteristics
        assert tool_model_info.supports_function_calling is True
        assert 'function-calling' in tool_model_info.tags
        
        # Test with general purpose model
        general_model_info = await registry.get_model_info('hermes3:8b', 'local')
        
        # Should be valid for planner/writer but not tool calling
        planner_valid, planner_issues = registry.validate_model_for_role(general_model_info, ModelRole.PLANNER)
        tool_valid, tool_issues = registry.validate_model_for_role(general_model_info, ModelRole.TOOL_CALLING)
        
        print(f"Planner validation: {planner_valid}, issues: {planner_issues}")
        print(f"Tool validation: {tool_valid}, issues: {tool_issues}")
        print(f"General model supports function calling: {general_model_info.supports_function_calling}")
        
        assert planner_valid is True
        assert tool_valid is False
        # Should have some validation issue (warning about using recommended model)
        assert len(tool_issues) > 0
        assert any("xlam" in issue.lower() or "salesforce" in issue.lower() for issue in tool_issues)


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])