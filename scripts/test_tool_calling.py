import asyncio
import json
from openai import AsyncOpenAI
from typing import List, Dict

# --- Configuration ---
# Add the simple, local names of the Ollama models you want to test.
MODELS_TO_TEST: List[str] = [
    "hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
    "hf.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF:Q8_0",
    "hf.co/bartowski/Phi-3-medium-4k-instruct-GGUF:Q6_K",
]

# The Ollama server endpoint.
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"

# --- Test Tool Definition ---
# A simple function schema for the model to call.
GET_WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather for a specific location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g., San Francisco, CA",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature.",
                },
            },
            "required": ["location", "unit"],
        },
    },
}

async def test_model_tool_calling(client: AsyncOpenAI, model_name: str):
    """
    Tests a single Ollama model for its ability to make a tool call.
    """
    print(f"--- Testing Model: {model_name} ---")
    
    messages = [
        {"role": "user", "content": "What is the weather like in Toronto, Ontario in Celsius?"}
    ]
    
    try:
        # Make the API call requesting a tool response
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=[GET_WEATHER_TOOL],
            tool_choice="auto",
            temperature=0.0,
        )
        
        # --- Verification ---
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            print(f"  [FAILURE] ❌ Model did not return a tool call.")
            print(f"  -> Response: {response_message.content}")
            return

        # Check if the tool call is well-formed
        call = tool_calls[0]
        if call.function.name == "get_current_weather":
            print(f"  [SUCCESS] ✅ Model correctly called the tool '{call.function.name}'.")
            try:
                # Try to parse the arguments to ensure they are valid JSON
                args = json.loads(call.function.arguments)
                print(f"  -> Arguments: {args}")
                if "location" in args and "unit" in args:
                    print("  -> Arguments are valid.")
                else:
                    print("  [WARNING] ⚠️ Arguments are missing required fields.")
            except json.JSONDecodeError:
                print(f"  [FAILURE] ❌ Arguments were not valid JSON: {call.function.arguments}")
        else:
            print(f"  [FAILURE] ❌ Model called an unexpected tool: '{call.function.name}'.")

    except Exception as e:
        print(f"  [CRITICAL FAILURE] 🚨 An API error occurred: {e}")

async def main():
    """
    Main function to initialize the client and run tests for all models.
    """
    print("Initializing Ollama client...")
    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    
    print("\nStarting tool-calling capability tests for all configured models...")
    
    for model in MODELS_TO_TEST:
        await test_model_tool_calling(client, model)
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())