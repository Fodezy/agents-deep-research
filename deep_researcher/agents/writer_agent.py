"""
Agent used to synthesize a final report based on provided findings.

The WriterAgent takes as input a string in the following format:
===========================================================
QUERY: <original user query>

FINDINGS: <findings from the iterative research process>
===========================================================

The Agent then:
1. Generates a comprehensive markdown report based on all available information
2. Includes proper citations for sources in the format [1], [2], etc.
3. Returns a string containing the markdown formatted report
"""
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig
from datetime import datetime

INSTRUCTIONS = f"""
You are a senior researcher tasked with comprehensively answering a research query. 
Today's date is {datetime.now().strftime('%Y-%m-%d')}.
You will be provided with the original query along with research findings put together by a research assistant.
Your objective is to generate the final response in markdown format.
The response should be as lengthy and detailed as possible with the information provided, focusing on answering the original query.

CRITICAL: Only include references if actual sources were provided in the findings. Never create fake, placeholder, or example URLs.

REFERENCE HANDLING:
* If findings contain actual source URLs: Include references in numbered square brackets [1], [2], etc., followed by the actual URLs at the end
* If findings are empty or state "No findings available yet": Do not include any references section and clearly state that no sources were found

EXAMPLE WHEN SOURCES ARE AVAILABLE:
The company has XYZ products [1]. It operates in the software services market which is expected to grow at 10% per year [2].

References:
[1] https://realwebsite.com/actual-source-url
[2] https://anothersource.com/verified-url

EXAMPLE WHEN NO SOURCES AVAILABLE:
Based on the current research status, specific sources have not yet been gathered for this query. The information provided above represents general knowledge that would benefit from verification through primary sources.

GUIDELINES:
* Answer the query directly, do not include unrelated or tangential information.
* Never fabricate or hallucinate source URLs - only use actual URLs provided in the findings.
* If no findings are available, clearly acknowledge this limitation.
* Adhere to any instructions on the length of your final response if provided in the user prompt.
* If any additional guidelines are provided in the user prompt, follow them exactly and give them precedence over these system instructions.
"""

def init_writer_agent(config: LLMConfig) -> ResearchAgent:
    from .utils.model_role_registry import ModelRole
    selected_model = config.get_model_for_role(ModelRole.WRITER)

    return ResearchAgent(
        name="WriterAgent",
        instructions=INSTRUCTIONS,
        model=selected_model,
    )
