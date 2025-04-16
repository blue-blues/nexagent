# Structured Output Format

This document describes the structured output format used in the Nexagent application to provide a clear separation between implementation steps and the final output.

## Overview

The structured output format consists of two main sections:

1. **Implementation Steps**: This section contains the detailed steps taken by the agent to solve the task. It includes the reasoning process, intermediate results, and any other information that helps understand how the agent arrived at the solution.

2. **Final Output**: This section contains only the final result or answer to the user's query, without any implementation details or intermediate steps.

## Format

The structured output follows this format:

```markdown
## Implementation Steps

[Detailed implementation steps, reasoning, intermediate results, etc.]

---

## Final Output

[Final result or answer to the user's query]
```

## Implementation

The structured output format is implemented using the `WebOutputFormatter.create_structured_output` method, which takes any output text and formats it with clear sections for implementation steps and final output.

### Usage

```python
from app.agent.web_output import WebOutputFormatter

# Format any output with clear sections
structured_output = WebOutputFormatter.create_structured_output(output_text)
```

### Integration

The structured output format is integrated into the following components:

- **IntegratedAgent**: Uses the `format_output` method to format its output with clear sections
- **IntegratedFlow**: Ensures all responses (direct responses, agent results, and error messages) are formatted with clear sections
- **TaskBasedIntegratedFlow**: Formats all responses with clear sections

## Benefits

The structured output format provides several benefits:

1. **Clarity**: Users can easily distinguish between the implementation details and the final answer
2. **Readability**: The clear separation makes the output more readable and easier to understand
3. **Focus**: Users can focus on the final answer without being distracted by implementation details
4. **Transparency**: The implementation steps provide transparency into how the agent arrived at the solution

## Example

```markdown
## Implementation Steps

1. First, I'll search for information about the capital of France.
2. According to the search results, the capital of France is Paris.
3. I'll verify this information from multiple sources to ensure accuracy.

---

## Final Output

The capital of France is Paris. It is located in the north-central part of the country and has been the capital since 987 CE when Hugh Capet, the first king of the Capetian dynasty, made the city his seat of government.
```
