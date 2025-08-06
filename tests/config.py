"""
Model configuration file for tests.

Note: The appropriate environment variables need to be set up for each provider/model tested.
"""

# ==== FOR TESTING DIFFERENT MODEL PROVIDERS ====

# Different model providers and corresponding models to be tested
# Modify as needed to test different models
# Note that this list of models is only used for basic testing
PROVIDERS_TO_TEST = {
    'openai': 'gpt-4o-mini',
    'azureopenai': 'gpt-4o-mini',
    'anthropic': 'claude-3-5-sonnet-latest',
    'gemini': 'gemini-2.0-flash',
    'deepseek': 'deepseek-chat',
    'openrouter': 'google/gemma-3-4b-it:free',
}

# ==== FOR TESTING ALL AGENTS, TOOLS AND STRUCTURED OUTPUTS ====

SEARCH_PROVIDER = 'serper'

# Local models configuration for testing (compatible with HYBRID-07 5-model architecture)
# REASONING_MODEL: Complex reasoning and planning tasks
REASONING_MODEL_PROVIDER = 'local'
REASONING_MODEL = 'phi3:14b-medium-4k-instruct-q4_K_M'

# MAIN_MODEL: General purpose tasks, writing, analysis  
MAIN_MODEL_PROVIDER = 'local'
MAIN_MODEL = 'qwen3:14b'

# FAST_MODEL: Quick tasks, summarization
FAST_MODEL_PROVIDER = 'local'
FAST_MODEL = 'hermes3:8b'

# TOOL_CALLING_MODEL: Specialized for function calling (critical for pipeline)
TOOL_CALLING_MODEL_PROVIDER = 'local'
TOOL_CALLING_MODEL = 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'

# Legacy OpenAI configuration (uncomment to use instead of local models)
# REASONING_MODEL_PROVIDER = 'openai'
# REASONING_MODEL = 'gpt-4o-mini'
# MAIN_MODEL_PROVIDER = 'openai'
# MAIN_MODEL = 'gpt-4o-mini'
# FAST_MODEL_PROVIDER = 'openai'
# FAST_MODEL = 'gpt-4o-mini'