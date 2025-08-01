from .baseclass import ResearchAgent, ResearchRunner
from ..llm_config import LLMConfig, model_supports_structured_output
from .proofreader_agent import ReportDraft
from datetime import datetime
import re

INSTRUCTIONS = f"""
You are an expert report writer tasked with iteratively writing each section of a report. 
Today's date is {datetime.now().strftime('%Y-%m-%d')}.
You will be provided with:
1. The original research query
3. A final draft of the report containing the table of contents and all sections written up until this point (in the first iteration there will be no sections written yet)
3. A first draft of the next section of the report to be written

OBJECTIVE:
1. Write a final draft of the next section of the report with numbered citations in square brackets in the body of the report
2. Produce a list of references to be appended to the end of the report

CITATIONS/REFERENCES:
The citations should be in numerical order, written in numbered square brackets in the body of the report.
Separately, a list of all URLs and their corresponding reference numbers will be included at the end of the report.
Follow the example below for formatting.

GUIDELINES:
- You can reformat and reorganize the flow of the content and headings within a section to flow logically, but DO NOT remove details that were included in the first draft
- Only remove text from the first draft if it is already mentioned earlier in the report, or if it should be covered in a later section per the table of contents
- Ensure the heading for the section matches the table of contents
- Format the final output and references section as markdown
- Do not include a title for the reference section, just a list of numbered references

Only output markdown text, without JSON parsing or additional wrapping.
"""


def init_long_writer_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.fast_model

    # We expect raw markdown output, so we do not set output_type or parser
    return ResearchAgent(
        name="LongWriterAgent",
        instructions=INSTRUCTIONS,
        model=selected_model,
        tools=[],
        output_type=None,
        output_parser=None
    )


async def write_next_section(
    long_writer_agent: ResearchAgent,
    original_query: str,
    report_draft: str,
    next_section_title: str,
    next_section_draft: str,
) -> str:
    """Write the next section of the report and return raw markdown"""

    user_message = f"""
    <ORIGINAL QUERY>
    {original_query}
    </ORIGINAL QUERY>

    <CURRENT REPORT DRAFT>
    {report_draft or "No draft yet"}
    </CURRENT REPORT DRAFT>

    <TITLE OF NEXT SECTION TO WRITE>
    {next_section_title}
    </TITLE OF NEXT SECTION TO WRITE>

    <DRAFT OF NEXT SECTION>
    {next_section_draft}
    </DRAFT OF NEXT SECTION>
    """

    result = await ResearchRunner.run(
        long_writer_agent,
        user_message,
    )

    # return raw markdown directly
    return result.final_output  # assume it's plain markdown


async def write_report(
    long_writer_agent: ResearchAgent,
    original_query: str,
    report_title: str,
    report_draft: ReportDraft,
) -> str:
    """Write the final report by iteratively writing each section"""

    final_draft = f"# {report_title}\n\n" + \
                  "## Table of Contents\n\n" + \
                  "\n".join([f"{i+1}. {s.section_title}" for i, s in enumerate(report_draft.sections)]) + "\n\n"

    for section in report_draft.sections:
        section_markdown = await write_next_section(
            long_writer_agent,
            original_query,
            final_draft,
            section.section_title,
            section.section_content,
        )
        section_markdown = reformat_section_headings(section_markdown)
        final_draft += section_markdown + "\n\n"

    return final_draft


def reformat_section_headings(section_markdown: str) -> str:
    # promote all headings to start at level 2
    if not section_markdown.strip():
        return section_markdown
    first_heading_match = re.search(r'^(#+)\s', section_markdown, re.MULTILINE)
    if not first_heading_match:
        return section_markdown
    first_level = len(first_heading_match.group(1))
    adjust = 2 - first_level
    def repl(m):
        hashes, text = m.group(1), m.group(2)
        new_level = max(2, len(hashes) + adjust)
        return '#' * new_level + ' ' + text
    return re.sub(r'^(#+)\s(.+)$', repl, section_markdown, flags=re.MULTILINE)
