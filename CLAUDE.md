# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Command line usage (after pip install)
deep-researcher --mode deep --query "research topic" --max-iterations 5 --max-time 10 --verbose

# Direct Python execution
python -m deep_researcher.main --mode deep --query "research topic" --max-iterations 5 --max-time 10 --verbose

# Python API usage (see examples/ folder for complete examples)
python examples/deep_example.py
python examples/iterative_example.py
```

### Testing
```bash
# Run tests
python -m pytest tests/

# Run specific test files
python -m pytest tests/test_model_providers.py
python -m pytest tests/test_research_agents.py -v
```

### Docker (Optional)
```bash
# Run with SearchXNG provider
docker-compose up -d
# Set SEARCH_PROVIDER=searxng and SEARXNG_HOST=http://localhost:8080 in .env
```

## Architecture Overview

This is a multi-agent deep research system built on the OpenAI Agents SDK with support for multiple LLM providers and search engines.

### Core Components

**Two Main Research Modes:**
- `DeepResearcher`: Structured research with report planning and parallel section processing (for longer reports 20+ pages)
- `IterativeResearcher`: Continuous research loop for shorter reports (up to 5 pages/1000 words)

**Agent Architecture:**
- `ResearchAgent`/`ResearchRunner`: Custom base classes that extend OpenAI SDK agents with output parsing for non-structured-output models
- Knowledge Gap Agent: Identifies missing information in current research
- Tool Selector Agent: Strategically selects appropriate research tools
- Tool Agents: Specialized agents for web search and website crawling
- Writer Agent: Synthesizes findings into coherent reports
- Planner Agent: Creates structured report outlines (DeepResearcher only)
- Proofreader Agent: Final report compilation and editing

### Key Files Structure

**Core Logic:**
- `deep_researcher/deep_research.py`: DeepResearcher implementation
- `deep_researcher/iterative_research.py`: IterativeResearcher implementation  
- `deep_researcher/llm_config.py`: Multi-provider LLM configuration and client management
- `deep_researcher/main.py`: CLI entry point

**Agents:**
- `deep_researcher/agents/baseclass.py`: Custom Agent/Runner base classes with output parsing
- `deep_researcher/agents/*/`: Individual agent implementations
- `deep_researcher/agents/tool_agents/`: Specialized tool agents (search, crawl)

**Tools:**
- `deep_researcher/tools/web_search.py`: Web search with Serper/SearchXNG support and content scraping
- `deep_researcher/tools/crawl_website.py`: Website content extraction

### LLM Provider Configuration

The system supports multiple LLM providers through a unified configuration system:

**Supported Providers:** OpenAI, Azure OpenAI, DeepSeek, OpenRouter, Gemini, Anthropic, Perplexity, Hugging Face, Ollama/Local models

**Model Role Assignment:**
- Reasoning Model: Used for planning and knowledge gap analysis (default: o3-mini)
- Main Model: Used for writing and synthesis (default: gpt-4o) 
- Fast Model: Used for tool selection and filtering (default: gpt-4o-mini)

**Configuration via Environment or Runtime:**
```python
# Runtime configuration
llm_config = LLMConfig(
    search_provider="serper",
    reasoning_model_provider="openai",
    reasoning_model="o3-mini",
    main_model_provider="openai", 
    main_model="gpt-4o",
    fast_model_provider="openai",
    fast_model="gpt-4o-mini"
)
researcher = DeepResearcher(config=llm_config)
```

### Search Provider Configuration

**Supported Search Providers:**
- Serper (Google Search API) - requires SERPER_API_KEY
- SearchXNG (self-hosted) - requires SEARXNG_HOST URL
- OpenAI native search - requires SEARCH_PROVIDER=openai

### Custom Tool Development

To add custom research tools:
1. Create tool implementation in `deep_researcher/tools/`
2. Create tool agent in `deep_researcher/agents/tool_agents/`
3. Register in `init_tool_agents()` function in `deep_researcher/agents/tool_agents/__init__.py`
4. Update `tool_selector_agent.py` system prompt to include new tool description

### Important Notes

- The system runs many parallel API calls and web scraping operations - be mindful of rate limits
- Content is automatically trimmed to 10,000 characters per scraped page to manage token limits
- All models must support structured outputs or use custom output parsing via the ResearchAgent base class
- Tracing is supported for OpenAI models only via the --tracing flag
- The DeepResearcher runs IterativeResearcher instances in parallel for each report section