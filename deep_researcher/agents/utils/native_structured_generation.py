"""
Native Ollama structured outputs utility.

This module provides direct integration with Ollama's native structured outputs API,
bypassing the need for complex Outlines adapters while providing schema-guaranteed JSON output.
"""

from typing import Type, TypeVar, Any, Dict, Optional
from pydantic import BaseModel
import httpx
import json
import asyncio

T = TypeVar('T', bound=BaseModel)

# Global semaphore to limit concurrent requests to Ollama (prevent overload)
_ollama_semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests


async def generate_structured(
    base_url: str,
    model_name: str,
    messages: list[Dict[str, str]],
    schema_class: Type[T],
    temperature: float = 0.0,
    timeout: float = 300.0  # Increased to 5 minutes for complex structured generation
) -> T:
    """
    Generate structured output using native Ollama structured outputs.
    
    Args:
        base_url: Ollama base URL (e.g., "http://127.0.0.1:11434/v1")
        model_name: Name of the Ollama model to use
        messages: Chat messages in OpenAI format
        schema_class: Pydantic model class for output validation
        temperature: Generation temperature (0.0 for deterministic)
        timeout: Request timeout in seconds
    
    Returns:
        Validated instance of schema_class
        
    Raises:
        httpx.HTTPStatusError: If the API request fails
        json.JSONDecodeError: If the response is not valid JSON
        pydantic.ValidationError: If the response doesn't match the schema
    """
    # Convert OpenAI-compatible URL to native Ollama API endpoint
    ollama_url = f"{base_url.replace('/v1', '')}/api/chat"
    
    # Debug logging for connection issues
    print(f"[DEBUG] Native structured generation attempt:")
    print(f"  - Base URL: {base_url}")
    print(f"  - Ollama URL: {ollama_url}")
    print(f"  - Model: {model_name}")
    print(f"  - Timeout: {timeout}s")
    
    # Prepare the request payload
    payload = {
        "model": model_name,
        "messages": messages,
        "format": schema_class.model_json_schema(),
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    # Use semaphore to limit concurrent requests to Ollama
    async with _ollama_semaphore:
        print(f"[DEBUG] Acquired semaphore for {model_name} request")
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(ollama_url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                raw_content = data["message"]["content"]
                
                # Validate and return structured output
                print(f"[DEBUG] Released semaphore for {model_name} request")
                return schema_class.model_validate_json(raw_content)
                
            except httpx.TimeoutException as e:
                raise Exception(f"Ollama API timeout after {timeout}s - check if Ollama is running and responsive: {e}")
            except httpx.ConnectError as e:
                raise Exception(f"Cannot connect to Ollama at {ollama_url} - check if Ollama is running: {e}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ollama API request failed: {e.response.status_code} - {e.response.text}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response from Ollama: {e}")
            except Exception as e:
                raise Exception(f"Native structured generation failed: {e}")


def extract_model_info(selected_model: Any, config: Any) -> tuple[str, str]:
    """
    Extract base URL and model name from LLMConfig model objects.
    
    Works with the existing model role registry system.
    
    Args:
        selected_model: Model object from LLMConfig
        config: LLMConfig instance
        
    Returns:
        Tuple of (base_url, model_name)
    """
    # Get base URL from environment (LOCAL_MODEL_URL is a module-level constant)
    from ...llm_config import LOCAL_MODEL_URL
    base_url = LOCAL_MODEL_URL
    
    # Extract model name from selected_model
    if hasattr(selected_model, 'model'):
        model_name = selected_model.model
    elif hasattr(selected_model, 'model_name'):
        model_name = selected_model.model_name
    elif hasattr(selected_model, 'name'):
        model_name = selected_model.name
    else:
        # Fallback - extract from string representation
        model_str = str(selected_model)
        if '/' in model_str:
            model_name = model_str.split('/')[-1]
        else:
            model_name = model_str
    
    return base_url, model_name


class StructuredGenerationError(Exception):
    """Custom exception for structured generation failures."""
    pass


async def test_structured_generation(base_url: str, model_name: str) -> bool:
    """
    Test basic structured generation functionality.
    
    Args:
        base_url: Ollama base URL
        model_name: Model name to test with
        
    Returns:
        True if test passes, False otherwise
    """
    class TestSchema(BaseModel):
        message: str
        success: bool
    
    try:
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": "Reply with a test message saying 'Hello from structured generation' and success=true"}],
            schema_class=TestSchema,
            timeout=30.0
        )
        
        return result.success and "structured generation" in result.message.lower()
        
    except Exception as e:
        print(f"Structured generation test failed: {e}")
        return False