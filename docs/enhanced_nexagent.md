# Enhanced Nexagent Bot with Devika-Inspired Features

This document describes the enhancements made to the Nexagent Bot, inspired by Devika's capabilities. These enhancements enable the bot to autonomously transform high-level instructions into detailed execution plans, gather context from the web, generate multi-language code, and manage state with self-correction—all while providing clear progress updates to the user.

## Core Modules

### 1. AI Planning and Reasoning

The enhanced planning module provides advanced capabilities for breaking down complex tasks into detailed, executable steps:

- **Input Parsing**: Uses regex patterns and structured templates to extract key intents and requirements from user input.
- **Step Breakdown**: Generates multi-step plans with validation checkpoints and error handling.
- **Few-Shot Examples**: Incorporates stored example prompts to guide the model and constrain output format.

**Key Files:**
- `app/agent/enhanced_planning_agent.py`: Enhanced planning agent with validation and detailed metadata.
- `app/tool/input_parser.py`: Tool for parsing user input to extract structured information.
- `app/prompt/enhanced_planning.py`: Specialized prompts with few-shot examples.
- `app/flow/enhanced_planning_flow.py`: Flow that coordinates the enhanced planning process.

### 2. Contextual Keyword Extraction

This module analyzes user input and project context to extract critical keywords for web searches and code generation:

- **Extraction Process**: Uses domain-specific keyword lists and fallback algorithms (TF-IDF, frequency-based).
- **Validation**: Cross-checks extracted keywords against expected terms from project requirements.
- **Domain Detection**: Automatically detects the technical domain of the request.

**Key Files:**
- `app/tool/keyword_extractor.py`: Tool for extracting and analyzing keywords.
- `app/data/domain_keywords.json`: Domain-specific keyword lists.
- `app/agent/context_agent.py`: Agent that manages keyword extraction and context tracking.

### 3. Dynamic Agent State Tracking and Visualization

This module maintains real-time logs of agent actions and provides progress updates to the user:

- **State Logging**: Tracks agent actions, decisions, and intermediate outputs with timestamps.
- **User Feedback Loop**: Provides periodic summaries of current state and progress.
- **Visualization**: Formats state information for user consumption with progress bars and statistics.

**Key Files:**
- `app/state/agent_state_tracker.py`: Core state tracking functionality.
- `app/tool/state_visualizer.py`: Tool for generating formatted reports and visualizations.
- `app/agent/reporter_agent.py`: Agent that manages state reporting and user feedback.

## Implementation Status

The current implementation includes the first phase of enhancements:

- Enhanced Planning and Reasoning Module
- Contextual Keyword Extraction Module
- Dynamic Agent State Tracking and Visualization

Future phases will implement:
- Seamless Web Browsing and Information Gathering
- Multi-Language Code Generation
- Self-Healing and Error Recovery
- Modular Agent Coordination
- Natural Language Interaction and Continuous Feedback
- Project-Based Organization and Data Persistence

## Usage Example

```python
from app.agent.enhanced_planning_agent import EnhancedPlanningAgent
from app.agent.context_agent import ContextAgent
from app.agent.reporter_agent import ReporterAgent
from app.flow.enhanced_planning_flow import EnhancedPlanningFlow
from app.state.agent_state_tracker import AgentStateTracker

# Create a shared state tracker
state_tracker = AgentStateTracker()

# Create the agents
context_agent = ContextAgent()
planning_agent = EnhancedPlanningAgent()
reporter_agent = ReporterAgent(state_tracker=state_tracker)

# Create the planning flow
planning_flow = EnhancedPlanningFlow(
    agents={"planning": planning_agent},
    primary_agent_key="planning"
)

# Analyze the request
context_result = await context_agent.analyze_request("Build a REST API for a weather app")

# Create a plan
plan_result = await planning_flow.execute("Build a REST API for a weather app")

# Generate a progress report
progress_report = await reporter_agent.generate_progress_report()
```

## Demo

A demonstration script is available at `examples/enhanced_nexagent_demo.py`. This script showcases the enhanced planning, contextual keyword extraction, and state tracking capabilities.

To run the demo:

```bash
python examples/enhanced_nexagent_demo.py
```

## Integration with Existing Nexagent

The enhanced modules are designed to integrate seamlessly with the existing Nexagent architecture. They extend the base agent and tool classes, making them compatible with the current system while providing additional capabilities.

To integrate these enhancements into the main Nexagent system, the `IntegratedFlow` and `IntegratedAgent` classes can be updated to use the enhanced agents and tools when appropriate.

## Future Improvements

1. **Web Browsing Enhancement**: Implement stealth mode and structured data extraction for web research.
2. **Code Generation**: Create template-based code generation with syntax and quality checks.
3. **Self-Healing**: Add error detection and automatic correction capabilities.
4. **Agent Coordination**: Implement a coordinator for managing specialized agents.
5. **Project Organization**: Add project-based context storage and retrieval.

## Conclusion

The enhanced Nexagent Bot provides a more autonomous, context-aware, and self-monitoring system that can handle complex tasks with minimal user intervention. By breaking down high-level instructions into detailed plans, extracting relevant context, and tracking execution state, the bot can provide a more efficient and user-friendly experience.
