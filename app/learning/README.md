# Adaptive Learning System for Nexagent

This package provides a comprehensive learning framework that allows Nexagent to continuously improve its performance by learning from past interactions, successes, and failures.

## Overview

The Adaptive Learning System consists of five main components:

1. **Interaction Memory Store**: Stores and indexes past interactions, decisions, and outcomes for future reference.
2. **Performance Analytics Engine**: Analyzes the bot's performance across different tasks and domains to identify strengths and weaknesses.
3. **Strategy Adaptation Module**: Dynamically adjusts the bot's approach based on past performance data.
4. **Knowledge Distillation System**: Extracts generalizable knowledge from specific experiences.
5. **Feedback Integration Loop**: Incorporates explicit and implicit user feedback to guide learning.

## Components

### Interaction Memory Store (`memory_store.py`)

The Interaction Memory Store is responsible for storing and retrieving past interactions, decisions, and outcomes. It provides a rich source of examples for few-shot learning, enables pattern recognition across similar tasks, and supports analysis of successful vs. unsuccessful approaches.

Key features:
- Structured storage using SQLite
- Semantic search for finding similar interactions
- Statistical analysis of stored interactions
- Automatic cleanup of old records

### Performance Analytics Engine (`analytics.py`)

The Performance Analytics Engine analyzes the bot's performance across different tasks and domains to identify strengths and weaknesses. It provides data-driven insights for optimization, identifies areas needing improvement, and highlights successful strategies that can be reinforced.

Key features:
- Multiple performance metrics (success rate, execution time, etc.)
- Time series analysis of performance trends
- Strength/weakness identification
- Comprehensive reporting

### Strategy Adaptation Module (`strategy_adaptation.py`)

The Strategy Adaptation Module dynamically adjusts the bot's approach based on past performance data. It continuously improves performance over time, adapts to changing requirements and environments, and reduces repeated failures by learning from mistakes.

Key features:
- Strategy selection based on past performance
- Exploration vs. exploitation balancing
- A/B testing of strategy variants
- Parameter tuning based on performance

### Knowledge Distillation System (`knowledge_distillation.py`)

The Knowledge Distillation System extracts generalizable knowledge from specific experiences. It transforms specific experiences into general knowledge, improves transfer learning across domains, and reduces reliance on exact matches in past experiences.

Key features:
- Knowledge graph of concepts, entities, and relationships
- Template extraction from successful interactions
- Rule identification from patterns
- Knowledge application to new situations

### Feedback Integration Loop (`feedback_integration.py`)

The Feedback Integration Loop incorporates explicit and implicit user feedback to guide learning. It aligns improvements with user priorities, accelerates learning in critical areas, and builds user trust through visible responsiveness.

Key features:
- Explicit feedback collection (ratings, comments)
- Implicit feedback inference (corrections, repetitions)
- Feedback pattern analysis
- Improvement prioritization

## Main Integration Module (`__init__.py`)

The main integration module provides a unified interface to all learning components, simplifying integration with the main Nexagent application. It manages state persistence and loading, and provides high-level methods for common operations.

## Usage

### Basic Usage

```python
from app.learning import AdaptiveLearningSystem

# Create a learning system
learning_system = AdaptiveLearningSystem()

# Record an interaction
interaction = learning_system.record_interaction(
    user_prompt="What is the capital of France?",
    bot_response="The capital of France is Paris.",
    task_type="question_answering",
    tools_used=["web_search"],
    success=True,
    execution_time=1.2
)

# Select a strategy for a task
strategy = learning_system.select_strategy(
    task_type="code_generation",
    context={"language": "python"}
)

# Find similar interactions
similar_interactions = learning_system.find_similar_interactions(
    prompt="What is the capital of Spain?",
    limit=2
)

# Record feedback
feedback = learning_system.record_feedback(
    interaction_id=interaction.id,
    content="Great answer, thank you!",
    rating=5,
    positive=True
)

# Save the learning system state
learning_system.save_state("learning_state")
```

### Advanced Usage

For more advanced usage, see the [Adaptive Learning System documentation](../../docs/adaptive_learning_system.md) and the [integration guide](../../docs/adaptive_learning_integration.md).

## Maintenance

The Adaptive Learning System requires periodic maintenance to keep it running smoothly. This includes:

1. **Extracting Knowledge**: Analyze past interactions to extract generalizable knowledge.
2. **Analyzing Performance**: Generate reports on the system's performance.
3. **Cleaning Up Old Data**: Remove old interaction records to manage storage growth.

These tasks can be performed manually using the scripts in the `scripts` directory, or automatically using the `scheduled_maintenance.py` script.

## Future Enhancements

Future enhancements to the Adaptive Learning System could include:

1. **Advanced Semantic Search**: Implement more sophisticated embedding models for better similarity matching.
2. **Multi-Modal Learning**: Extend the system to learn from images, audio, and other modalities.
3. **Collaborative Learning**: Enable learning from multiple instances of the bot across different users.
4. **Explainable Adaptations**: Provide more detailed explanations of why certain adaptations were made.
5. **User-Specific Learning**: Tailor learning to individual users' preferences and needs.
