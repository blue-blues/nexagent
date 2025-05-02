# Nexagent Integration Modules

This package provides modules for integrating various components with Nexagent.

## Adaptive Nexagent Integration

The `AdaptiveNexagentIntegration` class integrates the Adaptive Learning System with Nexagent, allowing the bot to learn from past interactions and continuously improve its performance.

### Features

- **Continuous Learning**: The system learns from past interactions and improves over time
- **Adaptive Strategies**: The system adapts its approach based on past performance
- **Knowledge Extraction**: The system extracts generalizable knowledge from specific experiences
- **Feedback Collection**: The system collects and processes both explicit and implicit feedback
- **Performance Analysis**: The system analyzes its performance and identifies areas for improvement

### Usage

```python
from app.integration.adaptive_nexagent import AdaptiveNexagentIntegration
from app.flow.integrated_flow import IntegratedFlow
from app.flow.base import FlowType

# Initialize the integrated flow
flow = IntegratedFlow()

# Initialize the adaptive nexagent integration
adaptive_nexagent = AdaptiveNexagentIntegration(
    agents=flow.agents,
    tools=flow.integrated_agent.available_tools,
    flow_type=FlowType.INTEGRATED,
    state_directory="~/.nexagent/learning_state"
)

# Process a prompt
response = await adaptive_nexagent.process_prompt(
    prompt="What is the capital of France?",
    conversation_id="conversation_123",
    context={}
)

# Record feedback
feedback = adaptive_nexagent.record_explicit_feedback(
    interaction_id=response.get("interaction_id"),
    content="Great answer, thank you!",
    rating=5,
    positive=True
)

# Generate a performance report
report = adaptive_nexagent.generate_performance_report()

# Save the learning system state
adaptive_nexagent.save_state("~/.nexagent/learning_state")
```

### Configuration

The Adaptive Learning System can be configured through the `config/adaptive_learning.json` file. See the [documentation](../../docs/adaptive_learning_integration.md) for more information.

### Maintenance

The Adaptive Learning System requires periodic maintenance to keep it running smoothly. This includes:

1. **Extracting Knowledge**: Analyze past interactions to extract generalizable knowledge.
2. **Analyzing Performance**: Generate reports on the system's performance.
3. **Cleaning Up Old Data**: Remove old interaction records to manage storage growth.

These tasks can be performed manually using the scripts in the `scripts` directory, or automatically using the `scheduled_maintenance.py` script.

### Monitoring

The Adaptive Learning System can be monitored using the `monitor_adaptive_learning.py` script, which checks the health and performance of the system and sends alerts if any issues are detected.

### Web Integration

The Adaptive Learning System can be integrated with the web interface using the `app/web/adaptive_integration.py` module, which provides functions for processing prompts, collecting feedback, and generating reports.

### API Endpoints

The Adaptive Learning System provides API endpoints for the web interface, including:

- `/api/prompt`: Process a prompt through the adaptive nexagent integration
- `/api/feedback`: Record explicit feedback from a user
- `/api/performance-report`: Generate a comprehensive performance report
- `/api/feedback-report`: Generate a comprehensive feedback report
- `/api/improvement-priorities`: Get improvement priorities based on feedback
- `/api/save-state`: Save the state of the learning system
- `/api/extract-knowledge`: Extract knowledge from past interactions
- `/api/adapt-strategies`: Adapt strategies based on performance data
- `/api/task-types`: Get a list of all task types
- `/api/tools`: Get a list of all tools
- `/api/statistics`: Get statistics about the learning system

### UI Components

The Adaptive Learning System provides UI components for the web interface, including:

- `AdminDashboard`: Admin dashboard for the Adaptive Learning System
- `FeedbackForm`: Component for collecting user feedback on responses
- `PerformanceStats`: Component for displaying performance statistics
- `ReportViewer`: Component for viewing performance and feedback reports

## Future Enhancements

Future enhancements to the Adaptive Learning System could include:

1. **Advanced Semantic Search**: Implement more sophisticated embedding models for better similarity matching.
2. **Multi-Modal Learning**: Extend the system to learn from images, audio, and other modalities.
3. **Collaborative Learning**: Enable learning from multiple instances of the bot across different users.
4. **Explainable Adaptations**: Provide more detailed explanations of why certain adaptations were made.
5. **User-Specific Learning**: Tailor learning to individual users' preferences and needs.
