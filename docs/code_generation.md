# Code Generation Features

This document describes the code generation features implemented in Phase 2 of the Devika-inspired features for Nexagent.

## Overview

The code generation features provide advanced capabilities for generating, validating, and testing code in multiple programming languages. These features are designed to make Nexagent more effective at generating high-quality code that follows best practices and is free of syntax errors.

## Features

### 1. Template-Based Code Generation

The template-based code generation system provides a flexible way to generate code based on templates:

- **Template Library**: A collection of templates for common patterns in various programming languages
- **Parameter Substitution**: Automatically substitutes parameters in templates
- **Template Selection**: Intelligently selects the most appropriate template based on the task
- **Template Customization**: Allows customization of templates for specific needs

### 2. Syntax Validation

The syntax validation system ensures that generated code is syntactically correct:

- **Language-Specific Validators**: Validates code using language-specific tools
- **Error Reporting**: Provides detailed error reports with line numbers
- **Suggestion Generation**: Suggests fixes for syntax errors
- **Style Checking**: Checks code against style guidelines

### 3. Multi-Language Support

The code generation system supports multiple programming languages:

- **Python**: Full support for Python code generation and validation
- **JavaScript/TypeScript**: Support for JavaScript and TypeScript code generation and validation
- **Java**: Basic support for Java code generation
- **C#**: Basic support for C# code generation
- **C/C++**: Basic support for C and C++ code generation

### 4. Code Testing Framework

The code testing framework helps ensure that generated code works as expected:

- **Test Generation**: Automatically generates tests for generated code
- **Test Execution**: Executes tests in a secure sandbox environment
- **Test Result Reporting**: Reports test results with detailed information
- **Test Coverage Analysis**: Analyzes test coverage to ensure comprehensive testing

## Usage

### Template-Based Code Generation

```python
from app.tools.code.code_generation import CodeGeneration

async def generate_code():
    code_gen = CodeGeneration()
    
    # Generate code using a template
    result = await code_gen.execute(
        command="generate",
        language="python",
        description="A function to calculate the factorial of a number",
        template_type="function",
        template_params={
            "name": "factorial",
            "params": "n",
            "return_type": "int"
        }
    )
    
    print(result.output)
```

### Syntax Validation

```python
from app.tools.code.code_generation import CodeGeneration

async def validate_code():
    code_gen = CodeGeneration()
    
    # Validate code
    result = await code_gen.execute(
        command="validate",
        language="python",
        code="def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)"
    )
    
    print(result.output)
```

### Code Testing

```python
from app.tools.code.code_generation import CodeGeneration

async def test_code():
    code_gen = CodeGeneration()
    
    # Generate and test code
    result = await code_gen.execute(
        command="generate_and_test",
        language="python",
        description="A function to calculate the factorial of a number",
        test_cases=[
            {"input": "0", "expected": "1"},
            {"input": "5", "expected": "120"}
        ]
    )
    
    print(result.output)
```

## Configuration

### Code Generation Configuration

You can configure the code generation system in your `config.toml` file:

```toml
[code_generation]
# Default language for code generation
default_language = "python"

# Maximum code size in bytes
max_code_size = 10485760  # 10MB

# Timeout for code execution in seconds
execution_timeout = 30

# Enable/disable test generation
enable_test_generation = true

# Enable/disable style checking
enable_style_checking = true
```

## Templates

The code generation system includes templates for various programming languages and patterns. Here are some examples:

### Python Function Template

```python
def {{name}}({{params}}):
    """
    {{description}}
    
    Args:
        {{param_docs}}
    
    Returns:
        {{return_type}}: {{return_docs}}
    """
    # TODO: Implement function
    pass
```

### JavaScript Class Template

```javascript
/**
 * {{description}}
 */
class {{name}} {
    /**
     * Create a new {{name}}
     * @param {Object} options - The options for the {{name}}
     */
    constructor(options = {}) {
        // TODO: Initialize properties
    }
    
    /**
     * {{method_description}}
     * @param {Object} params - The parameters for the method
     * @returns {Object} The result
     */
    {{method_name}}(params = {}) {
        // TODO: Implement method
    }
}
```

## Limitations

- Code generation is limited by the quality of the templates and the description provided
- Syntax validation may not catch all semantic errors
- Test generation may not cover all edge cases
- Some languages have limited support for advanced features

## Future Enhancements

- Add support for more programming languages
- Improve template selection algorithm
- Enhance test generation with more sophisticated test cases
- Add support for more advanced code analysis
- Implement code optimization suggestions
