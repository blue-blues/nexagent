# Enhanced Nexagent Features

This document describes the enhanced features added to Nexagent, inspired by Devika's capabilities.

## Overview

The enhanced features include:

1. **AI Planning and Reasoning**
   - Enhanced planning tool with versioning and rollback capabilities
   - Plan validation and optimization
   - Comprehensive versioning with branching support

2. **Contextual Keyword Extraction**
   - Rule-based, TF-IDF, and semantic extraction methods
   - Validation against project context
   - Domain-specific keyword filtering

3. **Multi-Language Code Generation**
   - Template-based code generation
   - Syntax validation and testing
   - Documentation generation

4. **Self-Healing and Error Recovery**
   - Error detection and classification
   - Automatic fix suggestion and application
   - Learning from past errors

5. **Modular Agent Coordination**
   - Task breakdown and assignment
   - Role-based agent coordination
   - Dependency management between subtasks

6. **Custom Tool Creation Interface**
   - Template-based tool creation
   - Validation and documentation generation
   - Tool management

## Implementation Details

### AI Planning and Reasoning

The enhanced planning tool (`PlanningTool`) now includes:

- **Plan Versioning**: Create, list, and compare versions of plans
- **Rollback Capabilities**: Roll back to previous versions of plans
- **Branching Support**: Create and merge branches for parallel development
- **Version Tagging**: Tag versions for easy reference
- **Dependency Analysis**: Analyze dependencies between steps in a plan

### Contextual Keyword Extraction

The new `KeywordExtractionTool` provides:

- **Multiple Extraction Methods**:
  - Rule-based extraction using regex patterns
  - TF-IDF based extraction (if scikit-learn is available)
  - Semantic extraction using Sentence-BERT (if sentence-transformers is available)
- **Validation**: Validate extracted keywords against project context
- **Domain-Specific Filtering**: Filter keywords based on domain-specific knowledge

### Multi-Language Code Generation

The new `CodeGenerationTool` provides:

- **Multi-Language Support**: Generate code in multiple programming languages
- **Template-Based Generation**: Use templates for consistent code generation
- **Syntax Validation**: Validate generated code with syntax checking
- **Testing**: Test generated code in a sandbox environment
- **Documentation**: Generate documentation for code

### Self-Healing and Error Recovery

The new `SelfHealingTool` provides:

- **Error Detection**: Detect and classify errors
- **Fix Suggestion**: Suggest fixes for detected errors
- **Automatic Fixing**: Automatically apply fixes when possible
- **Learning**: Learn from past errors to improve future error detection and fixing

### Modular Agent Coordination

The new `ModularCoordinationFlow` provides:

- **Task Breakdown**: Break down complex tasks into subtasks
- **Role-Based Assignment**: Assign subtasks to specialized agents based on roles
- **Dependency Management**: Handle dependencies between subtasks
- **Result Aggregation**: Aggregate results from multiple agents

### Custom Tool Creation Interface

The new `CustomToolCreator` provides:

- **Template-Based Creation**: Create custom tools from templates
- **Validation**: Validate custom tool definitions
- **Documentation Generation**: Generate documentation for custom tools
- **Tool Management**: List, get, and delete custom tools

## Usage

### Testing the Enhanced Features

You can test the enhanced features using the provided test script:

```bash
python tests/test_enhanced_features.py
```

This script tests all the enhanced features and provides examples of how to use them.

### Using the Enhanced Features in Your Code

#### AI Planning and Reasoning

```python
from app.tool.planning import PlanningTool

# Create the planning tool
planning_tool = PlanningTool()

# Create a plan
result = await planning_tool.execute(
    command="create",
    plan_id="my_plan",
    title="My Plan",
    description="A plan for testing the enhanced planning tool",
    steps=["Step 1", "Step 2", "Step 3"]
)

# Create a version
result = await planning_tool.execute(
    command="create_version",
    plan_id="my_plan",
    version_id="v1",
    version_description="Initial version"
)

# Tag a version
result = await planning_tool.execute(
    command="tag_version",
    plan_id="my_plan",
    version_id="v1",
    tag_name="stable"
)
```

#### Contextual Keyword Extraction

```python
from app.tool.keyword_extraction import KeywordExtractionTool

# Create the keyword extraction tool
keyword_tool = KeywordExtractionTool()

# Extract keywords
result = await keyword_tool.execute(
    command="extract",
    text="Your text here",
    extraction_method="auto"
)

# Validate keywords
result = await keyword_tool.execute(
    command="validate",
    text="Your text here",
    project_context="Your project context here",
    extraction_method="auto"
)
```

#### Multi-Language Code Generation

```python
from app.tool.code_generation import CodeGenerationTool

# Create the code generation tool
code_gen_tool = CodeGenerationTool()

# Generate code
result = await code_gen_tool.execute(
    command="generate",
    language="python",
    description="Create a function that calculates the factorial of a number"
)

# Test the generated code
result = await code_gen_tool.execute(
    command="test",
    language="python",
    code="Your code here",
    test_input="print(factorial(5))"
)
```

#### Self-Healing and Error Recovery

```python
from app.tool.self_healing import SelfHealingTool

# Create the self-healing tool
self_healing_tool = SelfHealingTool()

# Detect an error
result = await self_healing_tool.execute(
    command="detect",
    error_message="Your error message here",
    tool_name="enhanced_browser"
)

# Suggest fixes
result = await self_healing_tool.execute(
    command="suggest",
    error_message="Your error message here",
    tool_name="enhanced_browser"
)

# Automatically fix an error
result = await self_healing_tool.execute(
    command="fix",
    error_message="Your error message here",
    tool_name="enhanced_browser",
    auto_fix=True
)
```

#### Modular Agent Coordination

```python
from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory

# Create agents
agents = {
    "coordinator": ToolCallAgent(
        name="coordinator",
        description="Coordinates tasks and manages the overall workflow"
    ),
    "researcher": ToolCallAgent(
        name="researcher",
        description="Researches information and gathers data"
    ),
    "coder": ToolCallAgent(
        name="coder",
        description="Generates and reviews code"
    )
}

# Create the flow
flow = FlowFactory.create_flow(
    flow_type=FlowType.MODULAR_COORDINATION,
    agents=agents
)

# Execute the flow
result = await flow.execute(
    prompt="Your prompt here"
)
```

#### Custom Tool Creation Interface

```python
from app.tool.custom_tool_creator import CustomToolCreator

# Create the custom tool creator
custom_tool_creator = CustomToolCreator()

# List available templates
result = await custom_tool_creator.execute(
    command="list_templates"
)

# Create a custom tool
result = await custom_tool_creator.execute(
    command="create",
    tool_name="text_analyzer",
    tool_description="Analyzes text and provides statistics",
    template="simple",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze"
            }
        },
        "required": ["text"]
    }
)

# List created tools
result = await custom_tool_creator.execute(
    command="list"
)
```

## Future Enhancements

Future enhancements to consider:

1. **Enhanced Web Browsing**:
   - Improved data extraction from web pages
   - Better handling of anti-scraping measures
   - Structured data extraction

2. **Advanced Code Generation**:
   - Support for more programming languages
   - Integration with code repositories
   - Code review and optimization

3. **Improved Self-Healing**:
   - More sophisticated error detection
   - Better fix suggestion algorithms
   - Integration with monitoring systems

4. **Enhanced Modular Coordination**:
   - More sophisticated task breakdown
   - Better role assignment algorithms
   - Improved result aggregation
