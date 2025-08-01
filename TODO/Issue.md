logged issue:

<task>
Address this knowledge gap: Current research on the practical implementation of quantum computers utilizing entanglement needs evaluation.
</task>
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\projects\agents-deep-research\deep_researcher\main.py", line 67, in <module>
    cli_entry()
  File "D:\projects\agents-deep-research\deep_researcher\main.py", line 64, in cli_entry
    asyncio.run(main())
  File "C:\Python312\Lib\asyncio\runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python312\Lib\asyncio\base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\main.py", line 44, in main
    report = await manager.run(query)
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\deep_research.py", line 44, in run
    research_results: List[str] = await self._run_research_loops(report_plan)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\deep_research.py", line 106, in _run_research_loops
    research_results = await asyncio.gather(
                       ^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\deep_research.py", line 102, in run_research_for_section
    return await iterative_researcher.run(**args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\iterative_research.py", line 181, in run
    selection_plan: AgentSelectionPlan = await self._select_agents(next_gap, query, background_context=background_context)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\iterative_research.py", line 273, in _select_agents
    result = await ResearchRunner.run(
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\agents\baseclass.py", line 65, in run
    return await starting_agent.parse_output(result)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\agents\baseclass.py", line 39, in parse_output
    parsed_output = self.output_parser(raw_output)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\projects\agents-deep-research\deep_researcher\agents\utils\parse_output.py", line 162, in parser
    raise OutputParserError(
deep_researcher.agents.utils.parse_output.OutputParserError: Failed to parse and validate output as AgentSelectionPlan
Problematic output: ```json

{

  "tasks": [

    {

      "gap": "Review quantum theory history",

      "agent": "WebSearchAgent",

      "query": "quantum entanglement origin theories",

      "entity_website": ""

    },

    {

      "gap": "Study wave-particle duality",

      "agent": "SiteCrawlerAgent",

      "query": "wave-particle duality explanation",

      "entity_website": "https://physicsworld.com"

    },

    {

      `"gap": "Analyze superposition principle",`

      `"agent": "`SiteCrawlerAgent`,

      `"query": "`quantum mechanics - superposition definition",

      `"entity_website": "`https://scienceworld.com"`" }```