from typing import Any, Callable, Optional, Union
from agents import Agent, Runner, RunResult
from agents.run_context import TContext
import json
import re
import logging
import os

# Runtime assertions import (with fallback if not available)
try:
    from .utils.runtime_assertions import (
        get_assertion_framework, 
        ModelRole, 
        RuntimeAssertionError,
        ModelRoleAssertion
    )
    RUNTIME_ASSERTIONS_AVAILABLE = True
except ImportError:
    RUNTIME_ASSERTIONS_AVAILABLE = False
    logging.warning("Runtime assertions not available - model validation disabled")

logger = logging.getLogger(__name__)


class ResearchAgent(Agent[TContext]):
    """
    This is a custom implementation of the OpenAI Agent class that supports output parsing
    for models that don't support structured output types. The user can specify an output_parser
    function that will be called with the raw output from the agent. This can run custom logic 
    such as cleaning up the output and converting it to a structured JSON object.

    Needs to be run with the ResearchRunner to work.
    """

    def __init__(
        self,
        *args,
        output_parser: Optional[Callable[[str], Any]] = None,
        summariser=None,
        structured_generator: Optional[Callable] = None,
        role: Optional[ModelRole] = None,
        **kwargs
    ):
        # The output_parser is a function that only takes effect if output_type is not specified
        self.output_parser = output_parser
        self.summariser = summariser
        self.structured_generator = structured_generator
        self.role = role

        # If both are specified, we raise an error - they can't be used together
        if self.output_parser and kwargs.get("output_type"):
            raise ValueError("Cannot specify both output_parser and output_type")

        # Handle callable instructions for dynamic prompt generation
        if "instructions" in kwargs and callable(kwargs["instructions"]):
            self._dynamic_instructions = kwargs["instructions"]
            kwargs["instructions"] = ""  # Placeholder for now
        else:
            self._dynamic_instructions = None

        super().__init__(*args, **kwargs)
    
    def infer_agent_role(self) -> Optional[ModelRole]:
        """Infer the agent's role based on its name, tools, and capabilities."""
        if self.role:
            return self.role
        
        # Don't try to import if not available
        if not RUNTIME_ASSERTIONS_AVAILABLE:
            return None
        
        agent_name = getattr(self, 'name', '').lower()
        
        # Check for tool usage (indicates tool calling role)
        has_tools = bool(getattr(self, 'tools', []))
        if has_tools:
            return ModelRole.TOOL_CALLING
        
        # Check agent name patterns
        if any(keyword in agent_name for keyword in ['tool', 'search', 'crawl', 'selector']):
            return ModelRole.TOOL_CALLING
        elif any(keyword in agent_name for keyword in ['plan', 'strategy']):
            return ModelRole.PLANNER
        elif any(keyword in agent_name for keyword in ['summar', 'extract']):
            return ModelRole.SUMMARISER
        elif any(keyword in agent_name for keyword in ['writ', 'report', 'document']):
            return ModelRole.WRITER
        
        # Default to general purpose role
        return ModelRole.PLANNER

    async def parse_output(self, run_result: RunResult) -> RunResult:
        """
        Process the RunResult by applying the output_parser to its final_output if specified.
        This preserves the RunResult structure while modifying its content.
        """
        if self.output_parser:
            raw_output = run_result.final_output
            parsed_output = self.output_parser(raw_output)
            run_result.final_output = parsed_output
        return run_result

    async def process_large_content(self, content: str, context: str = "") -> str:
        """Process large content through hierarchical summariser if available"""
        if self.summariser:
            # Use TokenChunker estimation for consistency
            estimated_chunks = self.summariser.chunker.estimate_chunks(content)
            if estimated_chunks > 1:  # More than one chunk = needs summarisation
                result = await self.summariser.summarise_large_content(content, context)
                return result["final_summary"]
        return content  # Return as-is for small content


class ResearchRunner(Runner):
    @classmethod
    async def run(cls, *args, **kwargs) -> RunResult:
        starting_agent = kwargs.get("starting_agent") or (args[0] if len(args) > 0 else None)
        
        # RUNTIME ASSERTION: Validate model-role compatibility before execution
        await cls._validate_agent_model_compatibility(starting_agent)

        # Handle structured generator call (Outlines path)
        if isinstance(starting_agent, ResearchAgent) and starting_agent.structured_generator:
            try:
                input_data = kwargs.get("input") or (args[1] if len(args) > 1 else "")
                structured_result = starting_agent.structured_generator(input_data)

                class StructuredResult:
                    def __init__(self, output):
                        self.final_output = output

                    def final_output_as(self, output_type):
                        return self.final_output

                return StructuredResult(structured_result)
            except Exception as e:
                print(f"[WARN] Structured generation failed: {e}, falling back to standard parsing", flush=True)
                # continue to regular flow

        # Handle dynamic instructions
        dynamic_used = False
        if isinstance(starting_agent, ResearchAgent) and getattr(starting_agent, "_dynamic_instructions", None):
            input_data = kwargs.get("input") or (args[1] if len(args) > 1 else "")
            dynamic_prompt = starting_agent._dynamic_instructions(input_data)
            original_instructions = starting_agent.instructions
            starting_agent.instructions = dynamic_prompt
            dynamic_used = True
            try:
                print("[DEBUG] Invoking base Runner.run with dynamic instructions", flush=True)
                result = await Runner.run(*args, **kwargs)
            finally:
                starting_agent.instructions = original_instructions
        else:
            print("[DEBUG] Invoking base Runner.run", flush=True)
            result = await Runner.run(*args, **kwargs)

        print("[DEBUG] Raw final_output from base runner:", getattr(result, "final_output", None), flush=True)
        
        # PIPELINE DEBUG: Log raw responses to find function call format
        if hasattr(result, 'raw_responses') and result.raw_responses:
            print("[PIPELINE_DEBUG] Raw responses from base runner:", flush=True)
            for i, resp in enumerate(result.raw_responses):
                print(f"  Response {i}: type={type(resp)}", flush=True)
                if hasattr(resp, 'output'):
                    print(f"    output type: {type(resp.output)}", flush=True)
                    if hasattr(resp.output, '__iter__') and not isinstance(resp.output, str):
                        print(f"    output items ({len(resp.output)}):", flush=True)
                        for j, item in enumerate(resp.output):
                            print(f"      Item {j}: type={type(item).__name__}", flush=True)
                            if hasattr(item, 'name'):
                                print(f"        name: {getattr(item, 'name', None)}", flush=True)
                            if hasattr(item, 'function_call'):
                                print(f"        function_call: {getattr(item, 'function_call', None)}", flush=True)
                            if hasattr(item, 'content'):
                                content = getattr(item, 'content', '')
                                print(f"        content: {str(content)[:200]}...", flush=True)
                    else:
                        print(f"    output content: {str(resp.output)[:200]}...", flush=True)

        # --- Fallback: resolve function call JSON manually if tool execution didn't happen ---
        if isinstance(starting_agent, ResearchAgent):
            raw_output = getattr(result, "final_output", "")
            func_call = None
            if isinstance(raw_output, str):
                match = re.search(
                    r'\{[^}]*"name"\s*:\s*"(?P<name>[^"]+)"[^}]*"arguments"\s*:\s*(?P<args>\{.*?\})\}',
                    raw_output,
                    re.DOTALL,
                )
                if match:
                    try:
                        func_call = {
                            "name": match.group("name"),
                            "arguments": json.loads(match.group("args")),
                        }
                        print(f"[DEBUG] Extracted function call fallback: {func_call}", flush=True)
                    except json.JSONDecodeError:
                        func_call = None

            if func_call:
                tool_name = func_call["name"]
                arguments = func_call["arguments"]

                matching_tool = None
                for tool in starting_agent.tools:
                    candidate_names = set()

                    # Collect possible names from common attributes
                    if hasattr(tool, "name_override") and getattr(tool, "name_override", None):
                        candidate_names.add(getattr(tool, "name_override"))
                    if hasattr(tool, "name"):
                        candidate_names.add(getattr(tool, "name"))
                    if hasattr(tool, "__name__"):
                        candidate_names.add(getattr(tool, "__name__", ""))
                    # Some wrappers store the underlying function
                    if hasattr(tool, "func") and hasattr(tool.func, "__name__"):
                        candidate_names.add(tool.func.__name__)

                    print(f"[DEBUG] Tool candidates for '{tool_name}': {candidate_names}", flush=True)

                    if tool_name in candidate_names:
                        matching_tool = tool
                        break

                if not matching_tool:
                    print(f"[DEBUG] No matching tool found for function call name '{tool_name}'", flush=True)
                else:
                    print(f"[DEBUG] Manually invoking tool '{tool_name}' with args: {arguments}", flush=True)
                    tool_result = None
                    if hasattr(matching_tool, "on_invoke_tool"):
                        try:
                            tool_result = await matching_tool.on_invoke_tool(None, arguments)
                        except Exception as e:
                            print(f"[DEBUG] on_invoke_tool error: {e}", flush=True)
                    if tool_result is None and hasattr(matching_tool, "func"):
                        try:
                            # Assume single positional argument
                            first_arg = list(arguments.values())[0]
                            tool_result = await matching_tool.func(first_arg)
                        except Exception as e:
                            print(f"[DEBUG] direct func invocation error: {e}", flush=True)

                    if tool_result is not None:
                        followup_text = (
                            f"Function `{tool_name}` was called with {json.dumps(arguments)} and returned:\n{tool_result}"
                        )
                        updated_kwargs = dict(kwargs)
                        base_input = updated_kwargs.get("input") or (args[1] if len(args) > 1 else "")
                        if isinstance(base_input, str):
                            updated_input = base_input + "\n\n" + followup_text
                            updated_kwargs["input"] = updated_input
                        else:
                            updated_kwargs.setdefault("additional_context", []).append(followup_text)

                        print("[DEBUG] Re-running agent to consume tool result fallback.", flush=True)
                        result = await Runner.run(*args, **updated_kwargs)
                    else:
                        print(f"[DEBUG] Tool '{tool_name}' invocation produced no result.", flush=True)


        # Apply ResearchAgent parser if needed
        if isinstance(starting_agent, ResearchAgent):
            return await starting_agent.parse_output(result)

        return result
    
    @classmethod
    async def _validate_agent_model_compatibility(cls, agent) -> None:
        """Validate that the agent's model is compatible with its inferred role."""
        if not RUNTIME_ASSERTIONS_AVAILABLE:
            return
        
        # Skip validation if not a ResearchAgent
        if not isinstance(agent, ResearchAgent):
            return
        
        # Check if runtime assertions are disabled via environment variable
        if os.getenv('DISABLE_RUNTIME_ASSERTIONS', '').lower() in ('true', '1', 'yes'):
            logger.info("Runtime assertions disabled via environment variable")
            return
        
        try:
            # Infer the agent's role
            inferred_role = agent.infer_agent_role()
            if not inferred_role:
                logger.debug("Could not infer agent role, skipping validation")
                return
            
            # Extract model information from the agent
            model_info = cls._extract_model_info(agent)
            if not model_info:
                logger.warning("Could not extract model information from agent, skipping validation")
                return
            
            model_id, provider = model_info
            
            # Get assertion framework and validate
            framework = get_assertion_framework()
            
            logger.info(f"Validating {inferred_role.value} model compatibility: {model_id}")
            
            assertion = ModelRoleAssertion(
                role=inferred_role,
                model_id=model_id,
                provider=provider,
                required=True
            )
            
            result = await framework.validate_single_assertion(assertion)
            
            if not result.passed:
                # Create actionable error message
                error_msg = f"Model validation failed for {inferred_role.value} role"
                error = RuntimeAssertionError(error_msg, [result])
                
                logger.error("CRITICAL: Model-Role Validation Failed")
                logger.error(f"Agent: {getattr(agent, 'name', 'Unknown')}")
                logger.error(f"Model: {model_id}")
                logger.error(f"Role: {inferred_role.value}")
                logger.error(f"Issue: {result.message}")
                
                for suggestion in result.suggestions:
                    logger.error(f"Suggestion: {suggestion}")
                
                raise error
            else:
                logger.info(f"Model validation passed: {result.message}")
                
        except RuntimeAssertionError:
            # Re-raise assertion errors
            raise
        except Exception as e:
            # Log other errors but don't block execution in production
            logger.warning(f"Runtime assertion validation failed with error: {e}")
            if os.getenv('FAIL_ON_ASSERTION_ERRORS', '').lower() in ('true', '1', 'yes'):
                raise
    
    @classmethod 
    def _extract_model_info(cls, agent) -> Optional[tuple[str, str]]:
        """Extract model ID and provider from agent."""
        try:
            # Try to get model from agent
            model = getattr(agent, 'model', None)
            if not model:
                return None
            
            # Extract model ID
            model_id = getattr(model, 'model', None)
            if not model_id:
                return None
            
            # Try to determine provider from base URL or other attributes
            provider = 'local'  # Default assumption
            
            if hasattr(model, '_client') and hasattr(model._client, '_base_url'):
                base_url = str(model._client._base_url)
                if 'openai.com' in base_url:
                    provider = 'openai'
                elif 'anthropic.com' in base_url:
                    provider = 'anthropic'
                elif 'localhost' in base_url or '127.0.0.1' in base_url:
                    provider = 'local'
            
            return model_id, provider
            
        except Exception as e:
            logger.debug(f"Failed to extract model info: {e}")
            return None
