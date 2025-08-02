from agents import set_tracing_disabled
set_tracing_disabled(True)

from typing import Union, Any, Callable, Awaitable
import os 


from agents import (
    OpenAIChatCompletionsModel,
    OpenAIResponsesModel,
    set_tracing_disabled,
    set_tracing_export_api_key,
)
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI

from .utils.os import get_env_with_prefix

load_dotenv(override=True)

OPENAI_API_KEY = get_env_with_prefix("OPENAI_API_KEY")
DEEPSEEK_API_KEY = get_env_with_prefix("DEEPSEEK_API_KEY")
OPENROUTER_API_KEY = get_env_with_prefix("OPENROUTER_API_KEY")
GEMINI_API_KEY = get_env_with_prefix("GEMINI_API_KEY")
ANTHROPIC_API_KEY = get_env_with_prefix("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = get_env_with_prefix("PERPLEXITY_API_KEY")
HUGGINGFACE_API_KEY = get_env_with_prefix("HUGGINGFACE_API_KEY")
LOCAL_MODEL_URL = get_env_with_prefix(
    "LOCAL_MODEL_URL"
)  # e.g. "http://localhost:11434/v1"
AZURE_OPENAI_ENDPOINT = get_env_with_prefix("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = get_env_with_prefix("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_KEY = get_env_with_prefix("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = get_env_with_prefix("AZURE_OPENAI_API_VERSION")

REASONING_MODEL_PROVIDER = get_env_with_prefix("REASONING_MODEL_PROVIDER", "openai")
REASONING_MODEL = get_env_with_prefix("REASONING_MODEL", "o3-mini")
MAIN_MODEL_PROVIDER = get_env_with_prefix("MAIN_MODEL_PROVIDER", "openai")
MAIN_MODEL = get_env_with_prefix("MAIN_MODEL", "gpt-4o")
FAST_MODEL_PROVIDER = get_env_with_prefix("FAST_MODEL_PROVIDER", "openai")
FAST_MODEL = get_env_with_prefix("FAST_MODEL", "gpt-4o-mini")

SEARCH_PROVIDER = get_env_with_prefix("SEARCH_PROVIDER", "serper")
SEARXNG_HOST    = get_env_with_prefix("SEARXNG_HOST")

supported_providers = [
    "openai",
    "deepseek",
    "openrouter",
    "gemini",
    "anthropic",
    "perplexity",
    "huggingface",
    "local",
    "azureopenai",
]

provider_mapping = {
    "openai": {
        "client": AsyncOpenAI,
        "model": OpenAIResponsesModel,
        "base_url": None,
        "api_key": OPENAI_API_KEY,
    },
    "deepseek": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.deepseek.com/v1",
        "api_key": DEEPSEEK_API_KEY,
    },
    "openrouter": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
    },
    "gemini": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY,
    },
    "anthropic": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.anthropic.com/v1/",
        "api_key": ANTHROPIC_API_KEY,
    },
    "perplexity": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.perplexity.ai/chat/completions",
        "api_key": PERPLEXITY_API_KEY,
    },
    "huggingface": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": HUGGINGFACE_API_KEY,
    },
    "local": {
        "client": AsyncOpenAI,
        "model": OpenAIChatCompletionsModel,
        # override the OpenAI SDK endpoint
        "base_url": LOCAL_MODEL_URL,
        # don’t send a (cloud) API key
        "api_key": "",
    },
    "azureopenai": {
        "client": AsyncAzureOpenAI,
        "model": OpenAIChatCompletionsModel,
        "api_key": AZURE_OPENAI_API_KEY,
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "azure_deployment": AZURE_OPENAI_DEPLOYMENT,
        "api_version": AZURE_OPENAI_API_VERSION,
    },
}

if OPENAI_API_KEY:
    set_tracing_export_api_key(OPENAI_API_KEY)
else:
    # If no OpenAI API key is provided, disable tracing
    set_tracing_disabled(True)

supported_search_providers = ["serper", "searxng", "openai"]


class LLMConfig:

    def __init__(
        self,
        search_provider: str,
        reasoning_model_provider: str,
        reasoning_model: str,
        main_model_provider: str,
        main_model: str,
        fast_model_provider: str,
        fast_model: str,
    ):
        if search_provider not in supported_search_providers:
            raise ValueError(f"Invalid search provider: {search_provider}")

        self.search_provider = search_provider
        if search_provider == "searxng":
            # stash the URL so your search‐agent can pick it up
            self.searxng_host = SEARXNG_HOST  # from the top‐level constant you just corrected

        if reasoning_model_provider not in supported_providers:
            raise ValueError(f"Invalid model provider: {reasoning_model_provider}")
        if main_model_provider not in supported_providers:
            raise ValueError(f"Invalid model provider: {main_model_provider}")
        if fast_model_provider not in supported_providers:
            raise ValueError(f"Invalid model provider: {fast_model_provider}")

        # Helper to init any provider model
        def _init_model(provider_key: str, model_name: str):
            m = provider_mapping[provider_key]
            client_cls = m["client"]
            kwargs = {k: v for k, v in m.items() if k not in ("model", "client")}
            client = client_cls(**kwargs)
            return m["model"](model=model_name, openai_client=client)

        self.reasoning_model = _init_model(reasoning_model_provider, reasoning_model)
        self.main_model = _init_model(main_model_provider, main_model)
        self.fast_model = _init_model(fast_model_provider, fast_model)

    async def call_with_functions(
        self,
        model_client: Any,
        messages: list[dict],
        functions: list[dict],
        function_call: Union[str, dict] = "auto",
        **chat_kwargs,
    ) -> Any:
        """
        Send a chat to `model_client`, passing function schemas when enabled.

        - Honors ENABLE_FUNCTION_CALLING env var.
        - If function calling is disabled or no functions provided, falls back to a normal chat call.
        """
        # Build the base kwargs for chat()
        api_kwargs = {"messages": messages, **chat_kwargs}

        # Conditionally include function schema
        if os.getenv("ENABLE_FUNCTION_CALLING", "false").lower() in ("1", "true") and functions:
            api_kwargs["functions"] = functions
            api_kwargs["function_call"] = function_call

        # Delegate to the underlying client
        return await model_client.chat(**api_kwargs)


def create_default_config() -> LLMConfig:
    return LLMConfig(
        search_provider=SEARCH_PROVIDER,
        reasoning_model_provider=REASONING_MODEL_PROVIDER,
        reasoning_model=REASONING_MODEL,
        main_model_provider=MAIN_MODEL_PROVIDER,
        main_model=MAIN_MODEL,
        fast_model_provider=FAST_MODEL_PROVIDER,
        fast_model=FAST_MODEL,
    )


def get_base_url(model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel]) -> str:
    """Utility function to get the base URL for a given model"""
    return str(model._client._base_url)


def model_supports_structured_output(
    model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel],
) -> bool:
    """Utility function to check if a model supports structured output"""
    # Force all models to use custom output parsing for consistency
    # This fixes tool execution issues with local models
    return False
    
    # Original logic (disabled for now):
    # structured_output_providers = ["openai.com", "anthropic.com"]
    # return any(
    #     provider in get_base_url(model) for provider in structured_output_providers
    # )


def get_summariser_tokenizer():
    """Get exact same tokenizer used by summariser models"""
    try:
        import tiktoken
        # Use GPT-4 tokenizer as it's compatible with most OpenAI models
        return tiktoken.encoding_for_model("gpt-4")
    except ImportError:
        # Fallback to simple character-based estimation if tiktoken not available
        class SimpleTokenizer:
            def __init__(self):
                self._text_cache = {}
            
            def encode(self, text: str) -> list:
                # Rough approximation: 3.5 chars per token
                tokens = list(range(len(text) // 4))
                self._text_cache[id(tokens)] = text
                return tokens
            
            def decode(self, tokens: list) -> str:
                # Try to find original text from cache
                text = self._text_cache.get(id(tokens))
                if text:
                    return text[:len(tokens) * 4]
                # Fallback: return empty string for unknown tokens
                return " " * (len(tokens) * 4)
        
        return SimpleTokenizer()
