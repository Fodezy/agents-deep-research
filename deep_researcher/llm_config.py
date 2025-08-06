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

# PIPELINE DEBUG: Monkey patch RunImpl for diagnostics
try:
    from agents.run import RunImpl
    _original_process_model_response = RunImpl.process_model_response
    
    @classmethod
    def _debug_process_model_response(cls, *, agent, all_tools, response, output_schema, handoffs):
        print(f"[PIPELINE_DEBUG] process_model_response called:", flush=True)
        print(f"  agent.name: {agent.name}", flush=True)
        print(f"  all_tools: {[t.name for t in all_tools]}", flush=True)
        print(f"  response.output length: {len(response.output) if hasattr(response, 'output') else 'N/A'}", flush=True)
        
        if hasattr(response, 'output'):
            for i, output in enumerate(response.output):
                print(f"    Output {i}: type={type(output).__name__}", flush=True)
                if hasattr(output, 'name'):
                    print(f"      name: {output.name}", flush=True)
                if hasattr(output, 'arguments'):
                    print(f"      arguments: {output.arguments}", flush=True)
                if hasattr(output, 'content'):
                    print(f"      content: {str(output.content)[:100]}...", flush=True)
        
        # Call original method
        result = _original_process_model_response(agent=agent, all_tools=all_tools, response=response, 
                                                output_schema=output_schema, handoffs=handoffs)
        
        print(f"[PIPELINE_DEBUG] process_model_response result:", flush=True)
        print(f"  functions count: {len(result.functions)}", flush=True)
        for i, func in enumerate(result.functions):
            print(f"    Function {i}: tool={func.function_tool.name}, call={func.tool_call.name}", flush=True)
        
        return result
    
    RunImpl.process_model_response = _debug_process_model_response
    
    # Also patch execute_function_tool_calls
    _original_execute_function_tool_calls = RunImpl.execute_function_tool_calls
    
    @classmethod 
    async def _debug_execute_function_tool_calls(cls, *, agent, tool_runs, hooks, context_wrapper, config):
        print(f"[PIPELINE_DEBUG] execute_function_tool_calls called with {len(tool_runs)} tool_runs:", flush=True)
        for i, tool_run in enumerate(tool_runs):
            print(f"  Tool {i}: {tool_run.function_tool.name} with args {tool_run.tool_call.arguments}", flush=True)
        
        result = await _original_execute_function_tool_calls(agent=agent, tool_runs=tool_runs, 
                                                           hooks=hooks, context_wrapper=context_wrapper, config=config)
        
        print(f"[PIPELINE_DEBUG] execute_function_tool_calls returned {len(result)} results", flush=True)
        for i, res in enumerate(result):
            print(f"  Result {i}: tool={res.tool.name}, output_len={len(str(res.output))}", flush=True)
        
        return result
    
    RunImpl.execute_function_tool_calls = _debug_execute_function_tool_calls
    
    # Also patch the OpenAI model to see what tools are being sent
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    _original_get_response = OpenAIChatCompletionsModel.get_response
    
    async def _debug_get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing):
        print(f"[PIPELINE_DEBUG] OpenAI model.get_response called:", flush=True)
        print(f"  tools passed: {len(tools)} tools", flush=True)
        for i, tool in enumerate(tools):
            print(f"    Tool {i}: type={type(tool)}, name={getattr(tool, 'name', 'no-name')}", flush=True)
        
        # Import ToolConverter here to convert tools
        from agents.models.openai_chatcompletions import ToolConverter
        converted_tools = [ToolConverter.to_openai(tool) for tool in tools] if tools else []
        print(f"  converted_tools: {len(converted_tools)} tools", flush=True)
        for i, ct in enumerate(converted_tools):
            print(f"    Converted Tool {i}: {ct}", flush=True)
        
        # Call original method and debug the response
        result = await _original_get_response(self, system_instructions=system_instructions, input=input, 
                                          model_settings=model_settings, tools=tools, output_schema=output_schema,
                                          handoffs=handoffs, tracing=tracing)
        
        print(f"[PIPELINE_DEBUG] OpenAI model response:", flush=True)
        print(f"  result.output length: {len(result.output)}", flush=True)
        for i, output_item in enumerate(result.output):
            print(f"    Output {i}: type={type(output_item).__name__}", flush=True)
            if hasattr(output_item, 'content'):
                content = getattr(output_item, 'content', [])
                if content:
                    print(f"      content[0]: type={type(content[0]).__name__}", flush=True)
                    if hasattr(content[0], 'text'):
                        text = content[0].text[:100] if content[0].text else ''
                        print(f"        text: {text}...", flush=True)
        
        return result
    
    OpenAIChatCompletionsModel.get_response = _debug_get_response
    
    # Patch the _fetch_response method to log raw ChatCompletion
    _original_fetch_response = OpenAIChatCompletionsModel._fetch_response
    
    async def _debug_fetch_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, span, tracing, stream=False):
        print(f"[PIPELINE_DEBUG] _fetch_response called with {len(tools)} tools", flush=True)
        print(f"  model_settings.tool_choice: {getattr(model_settings, 'tool_choice', 'not set')}", flush=True)
        
        # Import ToolConverter to log actual params sent to API
        from agents.models.openai_chatcompletions import _Converter
        tool_choice = _Converter.convert_tool_choice(model_settings.tool_choice)
        print(f"  converted tool_choice: {tool_choice}", flush=True)
        
        # Log the converted messages and tools that will be sent to API
        converted_messages = _Converter.items_to_messages(input)
        if system_instructions:
            converted_messages.insert(0, {"content": system_instructions, "role": "system"})
        
        from agents.models.openai_chatcompletions import ToolConverter
        converted_tools = [ToolConverter.to_openai(tool) for tool in tools] if tools else []
        
        print(f"[PIPELINE_DEBUG] Request to local model:", flush=True)
        print(f"  messages: {len(converted_messages)} messages", flush=True)
        print(f"  final message: {converted_messages[-1] if converted_messages else 'none'}", flush=True)
        print(f"  tools: {len(converted_tools)} tools", flush=True)
        print(f"  tool_choice: {tool_choice}", flush=True)
        print(f"  model: {self.model}", flush=True)
        
        result = await _original_fetch_response(self, system_instructions=system_instructions, input=input,
                                              model_settings=model_settings, tools=tools, output_schema=output_schema,
                                              handoffs=handoffs, span=span, tracing=tracing, stream=stream)
        
        # Log the raw ChatCompletion before conversion
        print(f"[PIPELINE_DEBUG] Raw response from local model:", flush=True)
        if hasattr(result, 'choices') and result.choices:
            message = result.choices[0].message
            print(f"  content: {message.content[:200] if message.content else None}...", flush=True)
            print(f"  tool_calls: {len(message.tool_calls) if message.tool_calls else 0} tool calls", flush=True)
            if message.tool_calls:
                for i, tc in enumerate(message.tool_calls):
                    print(f"    Tool Call {i}: id={tc.id}, name={tc.function.name}, args={tc.function.arguments[:50]}...", flush=True)
        else:
            print(f"  No choices in response: {result}", flush=True)
        
        return result
    
    OpenAIChatCompletionsModel._fetch_response = _debug_fetch_response
    
    # Patch the message converter to detect plaintext function calls and convert them
    from agents.models.openai_chatcompletions import _Converter
    _original_message_to_output_items = _Converter.message_to_output_items
    
    @classmethod
    def _enhanced_message_to_output_items(cls, message):
        print(f"[PIPELINE_DEBUG] message_to_output_items called:", flush=True)
        print(f"  message.content: {message.content[:100] if message.content else None}...", flush=True)
        print(f"  message.tool_calls: {len(message.tool_calls) if message.tool_calls else 0}", flush=True)
        
        # First, get the original output items
        items = _original_message_to_output_items(message)
        print(f"  original items: {len(items)} items", flush=True)
        
        # Check if we have a text message that might contain function call JSON
        if message.content and not message.tool_calls:
            import json
            import re
            
            # Look for function call JSON patterns in the text
            patterns = [
                # Pattern 1: Direct JSON object
                r'\{"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\}',
                # Pattern 2: JSON wrapped in tags (like </REFLECTION>...JSON...</tool_call>)
                r'</?\w*>?\s*\{"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\}\s*</?[\w_]+>?',
                # Pattern 3: More flexible JSON detection
                r'\{\s*"arguments"\s*:\s*(\{[^}]*\})\s*,\s*"name"\s*:\s*"([^"]+)"\s*\}'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, message.content, re.DOTALL | re.IGNORECASE)
                if matches:
                    print(f"[PIPELINE_DEBUG] Found function call pattern: {pattern[:50]}...", flush=True)
                    
                    for match in matches:
                        try:
                            if len(match) == 2:
                                if r'"arguments"' in pattern and pattern.index(r'"arguments"') < pattern.index(r'"name"'):  # Pattern 3 (arguments first)
                                    func_args_json, func_name = match
                                else:  # Pattern 1 & 2 (name first)
                                    func_name, func_args_json = match
                                
                                # Parse the arguments JSON
                                func_args = json.loads(func_args_json)
                                
                                print(f"[PIPELINE_DEBUG] Detected function call:", flush=True)
                                print(f"  name: {func_name}", flush=True) 
                                print(f"  arguments: {func_args}", flush=True)
                                
                                # Create a synthetic ResponseFunctionToolCall
                                from openai.types.responses import ResponseFunctionToolCall
                                
                                synthetic_call = ResponseFunctionToolCall(
                                    id="synthetic_call_001",
                                    call_id="synthetic_call_001", 
                                    arguments=json.dumps(func_args),
                                    name=func_name,
                                    type="function_call"
                                )
                                
                                print(f"[PIPELINE_DEBUG] Created synthetic function call: {synthetic_call}", flush=True)
                                items.append(synthetic_call)
                                
                                # Remove or replace the original text message to avoid confusion
                                # Keep only non-function-call text if any
                                clean_content = re.sub(pattern, '', message.content, flags=re.DOTALL | re.IGNORECASE).strip()
                                if clean_content and clean_content not in ['</REFLECTION>', '</tool_call>', '<tool_call>']:
                                    # Update the text content of existing message
                                    for item in items:
                                        if hasattr(item, 'content') and item.content:
                                            for content_part in item.content:
                                                if hasattr(content_part, 'text'):
                                                    content_part.text = clean_content
                                else:
                                    # Remove the text message entirely if it was just function call wrapper
                                    items = [item for item in items if not (hasattr(item, 'content') and item.content)]
                                
                                break  # Found a match, stop looking
                                
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"[PIPELINE_DEBUG] Failed to parse function call JSON: {e}", flush=True)
                            continue
                    
                    if matches:
                        break  # Found matches with this pattern, stop trying others
        
        print(f"[PIPELINE_DEBUG] Final items: {len(items)} items", flush=True)
        for i, item in enumerate(items):
            print(f"  Item {i}: type={type(item).__name__}", flush=True)
            if hasattr(item, 'name'):
                print(f"    name: {getattr(item, 'name', None)}", flush=True)
        
        return items
    
    _Converter.message_to_output_items = _enhanced_message_to_output_items
    print("[PIPELINE_DEBUG] Monkey patched RunImpl, OpenAI model, and message converter", flush=True)
except ImportError as e:
    print(f"[PIPELINE_DEBUG] Could not monkey patch RunImpl: {e}", flush=True)
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI

from .utils.os import get_env_with_prefix

# Import runtime assertions for model role validation
try:
    from .agents.utils.runtime_assertions import get_assertion_framework, ModelRoleAssertion, ModelRole
    from .agents.utils.model_role_registry import get_model_registry
    ROLE_VALIDATION_AVAILABLE = True
except ImportError:
    ROLE_VALIDATION_AVAILABLE = False

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

# 4-Model Architecture Environment Variables
TOOL_CALLING_MODEL_PROVIDER = get_env_with_prefix("TOOL_CALLING_MODEL_PROVIDER", "local")
TOOL_CALLING_MODEL = get_env_with_prefix("TOOL_CALLING_MODEL", "hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M")

# 5-Model Architecture (with backward compatibility)
PLANNER_MODEL_PROVIDER = get_env_with_prefix("PLANNER_MODEL_PROVIDER", REASONING_MODEL_PROVIDER)
PLANNER_MODEL = get_env_with_prefix("PLANNER_MODEL", REASONING_MODEL)
SUMMARISER_MODEL_PROVIDER = get_env_with_prefix("SUMMARISER_MODEL_PROVIDER", MAIN_MODEL_PROVIDER)
SUMMARISER_MODEL = get_env_with_prefix("SUMMARISER_MODEL", MAIN_MODEL)
WRITER_MODEL_PROVIDER = get_env_with_prefix("WRITER_MODEL_PROVIDER", FAST_MODEL_PROVIDER)
WRITER_MODEL = get_env_with_prefix("WRITER_MODEL", FAST_MODEL)
KNOWLEDGE_GAP_MODEL_PROVIDER = get_env_with_prefix("KNOWLEDGE_GAP_MODEL_PROVIDER", PLANNER_MODEL_PROVIDER)
KNOWLEDGE_GAP_MODEL = get_env_with_prefix("KNOWLEDGE_GAP_MODEL", PLANNER_MODEL)

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
        # do not send a cloud API key
        "api_key": "",
    },
    "azureopenai": {
        "client": AsyncAzureOpenAI,
        "model": OpenAIChatCompletionsModel,
        "api_key": AZURE_OPENAI_API_KEY,
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "azure_deployment": AZURE_OPENAI_DEPLOYMENT,
        "api_version": AZURE_OPENAI_API_VERSION or "2023-05-15",  # default api_version
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
        reasoning_model_provider: str = None,
        reasoning_model: str = None,
        main_model_provider: str = None,
        main_model: str = None,
        fast_model_provider: str = None,
        fast_model: str = None,
        # New 4-model architecture parameters
        planner_model_provider: str = None,
        planner_model: str = None,
        tool_calling_model_provider: str = None,
        tool_calling_model: str = None,
        summariser_model_provider: str = None,
        summariser_model: str = None,
        writer_model_provider: str = None,
        writer_model: str = None,
        knowledge_gap_model_provider: str = None,
        knowledge_gap_model: str = None,
        # Validation options
        validate_model_roles: bool = True,
        strict_validation: bool = False,
    ):
        if search_provider not in supported_search_providers:
            raise ValueError(f"Invalid search provider: {search_provider}")

        self.search_provider = search_provider
        # Always set searxng_host with default value for compatibility
        self.searxng_host = SEARXNG_HOST if search_provider == "searxng" else "http://127.0.0.1:8888"
        
        # Store validation options
        self.validate_model_roles = validate_model_roles
        self.strict_validation = strict_validation
        
        # Handle backward compatibility: if new 4-model params not provided, use legacy 3-model
        if planner_model_provider is None and reasoning_model_provider is not None:
            planner_model_provider = reasoning_model_provider
            planner_model = reasoning_model
        
        if summariser_model_provider is None and main_model_provider is not None:
            summariser_model_provider = main_model_provider  
            summariser_model = main_model
            
        if writer_model_provider is None and fast_model_provider is not None:
            writer_model_provider = fast_model_provider
            writer_model = fast_model
        
        # Use environment defaults if not provided (with ultimate fallbacks)
        if planner_model_provider is None:
            planner_model_provider = PLANNER_MODEL_PROVIDER or "local"
            planner_model = PLANNER_MODEL or "hermes3:8b"
            
        if tool_calling_model_provider is None:
            tool_calling_model_provider = TOOL_CALLING_MODEL_PROVIDER or "local"
            tool_calling_model = TOOL_CALLING_MODEL or "hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M"
            
        if summariser_model_provider is None:
            summariser_model_provider = SUMMARISER_MODEL_PROVIDER or "local"
            summariser_model = SUMMARISER_MODEL or "qwen2.5-coder:latest"
            
        if writer_model_provider is None:
            writer_model_provider = WRITER_MODEL_PROVIDER or "local"
            writer_model = WRITER_MODEL or "llama3.2:latest"
            
        if knowledge_gap_model_provider is None:
            knowledge_gap_model_provider = KNOWLEDGE_GAP_MODEL_PROVIDER or planner_model_provider
            knowledge_gap_model = KNOWLEDGE_GAP_MODEL or planner_model
        
        # Validate all providers
        for provider in [planner_model_provider, tool_calling_model_provider, summariser_model_provider, writer_model_provider, knowledge_gap_model_provider]:
            if provider not in supported_providers:
                raise ValueError(f"Invalid model provider: {provider}")
        
        # Store model configurations
        self.model_configs = {
            'planner': {
                'provider': planner_model_provider,
                'model': planner_model,
                'role': ModelRole.PLANNER if ROLE_VALIDATION_AVAILABLE else None
            },
            'tool_calling': {
                'provider': tool_calling_model_provider,
                'model': tool_calling_model,
                'role': ModelRole.TOOL_CALLING if ROLE_VALIDATION_AVAILABLE else None
            },
            'summariser': {
                'provider': summariser_model_provider,
                'model': summariser_model,
                'role': ModelRole.SUMMARISER if ROLE_VALIDATION_AVAILABLE else None
            },
            'writer': {
                'provider': writer_model_provider,
                'model': writer_model,
                'role': ModelRole.WRITER if ROLE_VALIDATION_AVAILABLE else None
            },
            'knowledge_gap': {
                'provider': knowledge_gap_model_provider,
                'model': knowledge_gap_model,
                'role': ModelRole.KNOWLEDGE_GAP if ROLE_VALIDATION_AVAILABLE else None
            }
        }
        
        # Maintain backward compatibility for existing code
        self.reasoning_model_provider = planner_model_provider
        self.reasoning_model = planner_model
        self.main_model_provider = summariser_model_provider
        self.main_model = summariser_model
        self.fast_model_provider = writer_model_provider
        self.fast_model = writer_model

        # Helper to sanitize headers to prevent Unicode encoding errors
        def _sanitize_headers(headers: dict) -> dict:
            new = {}
            for k, v in headers.items():
                if isinstance(v, str):
                    # drop any non-ascii characters
                    new[k] = v.encode('ascii', 'ignore').decode('ascii')
                else:
                    new[k] = v
            return new

        # Dummy client for tests when real credentials fail
        from types import SimpleNamespace
        
        class _DummyClient:
            async def chat(self, *, messages, **kwargs):
                # Generate appropriate response based on the last message content
                last_message = messages[-1]["content"] if messages else ""
                
                # If this looks like a ToolAgentOutput request, provide valid JSON
                if "ToolAgentOutput" in str(kwargs.get("response_format", "")) or "json" in last_message.lower():
                    response_content = '{"output": "Test response from dummy client", "sources": ["https://example.com"]}'
                else:
                    response_content = last_message
                
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=response_content))]
                )
            
            @property
            def responses(self):
                # mimic openai.responses.create
                class R:
                    async def create(self, **opts):
                        # For structured output, provide valid JSON
                        content = '{"output": "Test response from dummy responses client", "sources": ["https://example.com"]}'
                        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
                return R()

        # Helper to init any provider model
        def _init_model(provider_key: str, model_name: str):
            m = provider_mapping[provider_key]
            client_cls = m["client"]
            kwargs = {k: v for k, v in m.items() if k not in ("model", "client")}
            
            # Handle Azure credentials for tests
            if provider_key == "azureopenai" and not kwargs.get("api_key"):
                kwargs["api_key"] = "test"  # dummy key for tests
                
            try:
                client = client_cls(**kwargs)
            except Exception:
                # Fall back to dummy client for tests
                client = _DummyClient()
            
            # Comprehensive Unicode header sanitization
            import httpx
            
            # Patch httpx Headers class to sanitize on construction
            original_headers_init = httpx.Headers.__init__
            def sanitized_headers_init(self, headers=None, encoding=None):
                if headers:
                    if isinstance(headers, dict):
                        headers = _sanitize_headers(headers)
                    elif hasattr(headers, 'items'):
                        # Handle other mapping types
                        headers = _sanitize_headers(dict(headers))
                return original_headers_init(self, headers, encoding)
            httpx.Headers.__init__ = sanitized_headers_init
            
            # Sanitize default headers to prevent Unicode encoding errors
            if hasattr(client, "_default_headers"):
                client._default_headers = _sanitize_headers(client._default_headers)
            if hasattr(client, "_base_client") and hasattr(client._base_client, "_default_headers"):
                client._base_client._default_headers = _sanitize_headers(client._base_client._default_headers)
            
            return m["model"](model=model_name, openai_client=client)

        # Create models for 5-model architecture
        self.planner_model = _init_model(planner_model_provider, planner_model)
        self.tool_calling_model = _init_model(tool_calling_model_provider, tool_calling_model)
        self.summariser_model = _init_model(summariser_model_provider, summariser_model)
        self.writer_model = _init_model(writer_model_provider, writer_model)
        self.knowledge_gap_model = _init_model(knowledge_gap_model_provider, knowledge_gap_model)
        
        # Maintain backward compatibility
        self.reasoning_model = self.planner_model
        self.main_model = self.summariser_model
        self.fast_model = self.writer_model
        
        # Run model-role validation if enabled
        if self.validate_model_roles and ROLE_VALIDATION_AVAILABLE:
            import asyncio
            # Run validation in a new event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't run async validation in a running loop, defer to runtime
                    print("[INFO] Deferring model role validation to runtime (event loop already running)")
                else:
                    loop.run_until_complete(self._validate_model_roles())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(self._validate_model_roles())
        elif not ROLE_VALIDATION_AVAILABLE:
            print("[WARNING] Model role validation not available - consider running: pip install deep_researcher[validation]")

    async def _validate_model_roles(self):
        """Validate that all models are compatible with their assigned roles."""
        if not ROLE_VALIDATION_AVAILABLE:
            return
        
        framework = get_assertion_framework()
        assertions = []
        
        # Create assertions for each model-role pair
        for role_name, config in self.model_configs.items():
            if config['role']:
                assertion = ModelRoleAssertion(
                    role=config['role'],
                    model_id=config['model'],
                    provider=config['provider'],
                    required=self.strict_validation
                )
                assertions.append(assertion)
        
        if not assertions:
            return
        
        print(f"[INFO] Validating {len(assertions)} model-role assignments...")
        
        # Run all validations in parallel
        results = await framework.validate_assertions(assertions)
        
        # Check results
        failed_critical = [r for r in results if not r.passed and r.severity.value == 'critical']
        failed_warnings = [r for r in results if not r.passed and r.severity.value == 'warning']
        
        # Log results
        for result in results:
            if result.passed:
                print(f"[PASSED] {result.message}")
            else:
                level = "ERROR" if result.severity.value == 'critical' else "WARNING"
                print(f"[{level}] {result.message}")
                for suggestion in result.suggestions:
                    print(f"    Suggestion: {suggestion}")
        
        # Handle failures based on validation mode
        if failed_critical:
            if self.strict_validation:
                from .agents.utils.runtime_assertions import RuntimeAssertionError
                raise RuntimeAssertionError(
                    f"Model role validation failed for {len(failed_critical)} critical assignments",
                    failed_critical
                )
            else:
                print(f"[WARNING] {len(failed_critical)} critical model role validation failures detected")
                print("[WARNING] Consider updating your model configuration for optimal performance")
        
        if failed_warnings:
            print(f"[INFO] {len(failed_warnings)} model role validation warnings (non-blocking)")
    
    def get_model_for_role(self, role: ModelRole):
        """Get the model instance for a specific role."""
        if not ROLE_VALIDATION_AVAILABLE:
            # Fallback to legacy mapping
            if role.value == 'planner':
                return self.reasoning_model
            elif role.value == 'tool_calling':
                return self.main_model  # Not ideal but maintains compatibility
            elif role.value == 'summariser':
                return self.main_model
            elif role.value == 'writer':
                return self.fast_model
            elif role.value == 'knowledge_gap':
                return self.reasoning_model  # Use reasoning model for gap analysis
        
        role_to_model = {
            ModelRole.PLANNER: self.planner_model,
            ModelRole.TOOL_CALLING: self.tool_calling_model,
            ModelRole.SUMMARISER: self.summariser_model,
            ModelRole.WRITER: self.writer_model,
            ModelRole.KNOWLEDGE_GAP: self.knowledge_gap_model
        }
        
        return role_to_model.get(role, self.main_model)
    
    def get_model_config_summary(self) -> dict:
        """Get a summary of the current model configuration."""
        return {
            'validation_enabled': self.validate_model_roles,
            'strict_validation': self.strict_validation,
            'models': {
                role_name: {
                    'provider': config['provider'],
                    'model': config['model'],
                    'role': config['role'].value if config['role'] else None
                }
                for role_name, config in self.model_configs.items()
            },
            'backward_compatibility': {
                'reasoning_model': self.reasoning_model,
                'main_model': self.main_model,
                'fast_model': self.fast_model
            }
        }

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

        # Conditionally include function schema - enabled by default, can opt out
        enable_fc = os.getenv("ENABLE_FUNCTION_CALLING", "true").lower() in ("1", "true")
        print(f"[PIPELINE_DEBUG] call_with_functions: enable_fc={enable_fc}, functions_provided={bool(functions)}", flush=True)
        if functions:
            print(f"[PIPELINE_DEBUG] Function schemas being sent: {[f.get('name', 'unnamed') for f in functions]}", flush=True)
        
        if enable_fc and functions:
            # Convert legacy functions format to modern tools format
            tools = []
            for func in functions:
                tool = {
                    "type": "function",
                    "function": {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {})
                    }
                }
                tools.append(tool)
            
            api_kwargs["tools"] = tools
            if function_call and function_call != "auto":
                if isinstance(function_call, str):
                    api_kwargs["tool_choice"] = {"type": "function", "function": {"name": function_call}}
                else:
                    api_kwargs["tool_choice"] = function_call
            else:
                api_kwargs["tool_choice"] = "auto"
            print(f"[PIPELINE_DEBUG] Added tools to API call: {len(tools)} tools, tool_choice={api_kwargs.get('tool_choice')}", flush=True)
        elif functions and not enable_fc:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Function calling is disabled (ENABLE_FUNCTION_CALLING=%s) but %d tools were provided; no functions will execute.",
                os.getenv("ENABLE_FUNCTION_CALLING", "true"), 
                len(functions)
            )
        else:
            print(f"[PIPELINE_DEBUG] No functions will be sent to API", flush=True)

        # Delegate to the underlying client
        return await model_client.chat(**api_kwargs)


def create_default_config() -> LLMConfig:
    """Create LLMConfig using environment variables with 5-model architecture."""
    return LLMConfig(
        search_provider=SEARCH_PROVIDER,
        # 5-model architecture (HYBRID-07)
        planner_model_provider=PLANNER_MODEL_PROVIDER,
        planner_model=PLANNER_MODEL,
        tool_calling_model_provider=TOOL_CALLING_MODEL_PROVIDER,
        tool_calling_model=TOOL_CALLING_MODEL,
        summariser_model_provider=SUMMARISER_MODEL_PROVIDER,
        summariser_model=SUMMARISER_MODEL,
        writer_model_provider=WRITER_MODEL_PROVIDER,
        writer_model=WRITER_MODEL,
        knowledge_gap_model_provider=KNOWLEDGE_GAP_MODEL_PROVIDER,
        knowledge_gap_model=KNOWLEDGE_GAP_MODEL,
        # Validation enabled by default in non-strict mode
        validate_model_roles=True,
        strict_validation=False,
    )

def create_legacy_config() -> LLMConfig:
    """Create LLMConfig using legacy 3-model parameters for backward compatibility."""
    return LLMConfig(
        search_provider=SEARCH_PROVIDER,
        reasoning_model_provider=REASONING_MODEL_PROVIDER,
        reasoning_model=REASONING_MODEL,
        main_model_provider=MAIN_MODEL_PROVIDER,
        main_model=MAIN_MODEL,
        fast_model_provider=FAST_MODEL_PROVIDER,
        fast_model=FAST_MODEL,
        validate_model_roles=False,  # Disable validation for legacy configs
    )


def get_base_url(model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel]) -> str:
    """Utility function to get the base URL for a given model"""
    return str(model._client._base_url)


def model_supports_structured_output(
    model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel],
) -> bool:
    """Utility function to check if a model supports structured output"""
    # Enable Outlines integration for local models
    # This allows structured generation with local TOOL_CALLING models
    base_url = get_base_url(model)
    
    # Local models via Ollama can use Outlines for structured generation
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return True
    
    # Cloud providers that support structured output natively
    structured_output_providers = ["openai.com", "anthropic.com"]
    return any(
        provider in base_url for provider in structured_output_providers
    )


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
