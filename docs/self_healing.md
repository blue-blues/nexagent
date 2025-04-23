# Self-Healing Features

This document describes the self-healing features implemented in Phase 2 of the Devika-inspired features for Nexagent.

## Overview

The self-healing features provide advanced capabilities for detecting, diagnosing, and automatically fixing errors that occur during the execution of tasks. These features are designed to make Nexagent more robust and resilient, allowing it to recover from errors and continue executing tasks without human intervention.

## Features

### 1. Error Detection and Classification

The error detection and classification system identifies and categorizes errors:

- **Error Taxonomy**: A comprehensive taxonomy of error types
- **Pattern Recognition**: Recognizes common error patterns
- **Context-Aware Detection**: Uses context to improve error detection
- **Severity Classification**: Classifies errors by severity
- **Impact Analysis**: Analyzes the impact of errors on the system

### 2. Fix Suggestion Algorithms

The fix suggestion algorithms provide recommendations for fixing errors:

- **Common Error Fix Patterns**: Predefined fixes for common errors
- **Language-Specific Fixes**: Fixes tailored to specific programming languages
- **Context-Aware Fix Generation**: Generates fixes based on the context
- **Multiple Suggestion Ranking**: Ranks multiple fix suggestions by confidence
- **Fix Explanation Generation**: Provides explanations for suggested fixes

### 3. Automatic Fixing

The automatic fixing system applies fixes to errors without human intervention:

- **Safe Auto-Fix Criteria**: Criteria for determining when it's safe to auto-fix
- **Automatic Fixing**: Applies fixes to errors that meet the criteria
- **Fix Verification**: Verifies that fixes actually resolve the errors
- **Rollback Capability**: Rolls back fixes that don't work
- **Fix History Tracking**: Tracks the history of fixes applied

### 4. Error Pattern Learning

The error pattern learning system improves error detection and fixing over time:

- **Pattern Storage**: Stores error patterns and successful fixes
- **Pattern Extraction**: Extracts patterns from new errors
- **Pattern Matching**: Matches new errors to known patterns
- **Pattern Effectiveness Tracking**: Tracks the effectiveness of patterns
- **Pattern Refinement**: Refines patterns based on results

## Usage

### Error Detection and Classification

```python
from app.tools.self_healing import SelfHealing

async def detect_error():
    self_healing = SelfHealing()
    
    # Detect and classify an error
    result = await self_healing.execute(
        command="detect",
        error_message="Connection timed out after 30 seconds",
        error_context="Attempting to connect to database"
    )
    
    print(result.output)
```

### Fix Suggestion

```python
from app.tools.self_healing import SelfHealing

async def suggest_fix():
    self_healing = SelfHealing()
    
    # Suggest fixes for an error
    result = await self_healing.execute(
        command="suggest_fix",
        error_message="Connection timed out after 30 seconds",
        error_context="Attempting to connect to database",
        tool_name="database_connector"
    )
    
    print(result.output)
```

### Automatic Fixing

```python
from app.tools.self_healing import SelfHealing

async def auto_fix():
    self_healing = SelfHealing()
    
    # Automatically fix an error
    result = await self_healing.execute(
        command="auto_fix",
        error_message="Connection timed out after 30 seconds",
        error_context="Attempting to connect to database",
        tool_name="database_connector",
        action="connect"
    )
    
    print(result.output)
```

## Configuration

### Self-Healing Configuration

You can configure the self-healing system in your `config.toml` file:

```toml
[self_healing]
# Maximum number of automatic fixes to attempt
max_auto_fixes = 5

# Confidence threshold for automatic fixing (0-1)
confidence_threshold = 0.7

# Enable/disable automatic fixing
enable_auto_fix = true

# Enable/disable error pattern learning
enable_pattern_learning = true

# Maximum number of error patterns to store
max_patterns = 1000
```

## Error Patterns

The self-healing system includes patterns for various types of errors. Here are some examples:

### Timeout Errors

```json
{
    "timeout": {
        "patterns": [
            "timed out",
            "timeout",
            "deadline exceeded",
            "operation took too long"
        ],
        "fixes": [
            {
                "description": "Increase timeout value",
                "action": "increase_timeout",
                "confidence": 0.8
            },
            {
                "description": "Break operation into smaller steps",
                "action": "break_operation",
                "confidence": 0.7
            }
        ]
    }
}
```

### Connection Errors

```json
{
    "connection": {
        "patterns": [
            "connection refused",
            "cannot connect",
            "connection error",
            "network error"
        ],
        "fixes": [
            {
                "description": "Retry connection",
                "action": "retry_connection",
                "confidence": 0.8
            },
            {
                "description": "Check network settings",
                "action": "check_network",
                "confidence": 0.7
            },
            {
                "description": "Use alternative endpoint",
                "action": "use_alternative",
                "confidence": 0.6
            }
        ]
    }
}
```

## Limitations

- Automatic fixing is limited to errors with known patterns
- Some errors may require human intervention
- Fix suggestions may not always be correct
- Error pattern learning requires a significant amount of data

## Future Enhancements

- Improve error detection with machine learning
- Enhance fix suggestion algorithms
- Add support for more complex error patterns
- Implement more sophisticated automatic fixing
- Improve error pattern learning with reinforcement learning
