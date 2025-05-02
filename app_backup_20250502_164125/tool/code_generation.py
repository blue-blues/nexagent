"""
Code Generation Tool for Nexagent.

This module provides functionality for generating code in multiple programming
languages based on natural language descriptions and templates.
"""

import json
import os
import re
import tempfile
from typing import Dict, List, Optional, Any, Union, Literal
from pathlib import Path

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.logger import logger
from app.sandbox.code_sandbox import CodeSandbox, default_code_sandbox


class CodeGenerationTool(BaseTool):
    """
    A tool for generating code in multiple programming languages.
    
    This tool provides functionality for:
    1. Generating code from natural language descriptions
    2. Using templates for consistent code generation
    3. Validating generated code with syntax checking
    4. Testing generated code in a sandbox environment
    5. Providing explanations and documentation for generated code
    """
    
    name: str = "code_generation"
    description: str = """
    Generates code in multiple programming languages based on natural language descriptions.
    Supports templates, syntax validation, testing, and documentation generation.
    """
    
    # Dependencies
    required_tools: List[str] = ["create_chat_completion"]
    
    # Code sandbox for testing generated code
    code_sandbox: CodeSandbox = Field(default_factory=lambda: default_code_sandbox)
    
    # Language-specific templates
    templates: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    
    # Supported languages
    supported_languages: List[str] = Field(
        default_factory=lambda: [
            "python", "javascript", "typescript", "java", "c#", "go", "rust",
            "html", "css", "sql", "bash", "powershell"
        ]
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        self._load_templates()
    
    def _load_templates(self):
        """Load code templates for supported languages."""
        self.templates = {
            "python": {
                "class": """
class {class_name}:
    \"\"\"
    {class_description}
    \"\"\"
    
    def __init__(self{init_params}):
        {init_body}
    
    def {method_name}(self{method_params}):
        \"\"\"
        {method_description}
        \"\"\"
        {method_body}
""",
                "function": """
def {function_name}({function_params}):
    \"\"\"
    {function_description}
    
    Args:
        {args_description}
    
    Returns:
        {returns_description}
    \"\"\"
    {function_body}
""",
                "script": """
#!/usr/bin/env python
\"\"\"
{script_description}
\"\"\"

{imports}

{body}

if __name__ == "__main__":
    {main_call}
"""
            },
            "javascript": {
                "class": """
class {class_name} {
  /**
   * {class_description}
   */
  constructor({init_params}) {
    {init_body}
  }
  
  /**
   * {method_description}
   */
  {method_name}({method_params}) {
    {method_body}
  }
}
""",
                "function": """
/**
 * {function_description}
 * 
 * @param {args_description}
 * @returns {returns_description}
 */
function {function_name}({function_params}) {
  {function_body}
}
""",
                "script": """
/**
 * {script_description}
 */

{imports}

{body}

{main_call}
"""
            },
            # Add templates for other languages as needed
        }
    
    async def execute(
        self,
        *,
        command: Literal["generate", "validate", "test", "document", "explain"],
        language: str,
        description: str,
        template_type: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
        test_input: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute the code generation tool.
        
        Args:
            command: The operation to perform (generate, validate, test, document, explain)
            language: The programming language to use
            description: Natural language description of the code to generate
            template_type: Optional template type to use (class, function, script)
            template_params: Optional parameters for the template
            code: Optional code to validate, test, document, or explain
            test_input: Optional input for testing the code
            
        Returns:
            ToolResult with generated code or operation result
        """
        try:
            # Validate language
            if language.lower() not in [lang.lower() for lang in self.supported_languages]:
                return ToolResult(error=f"Unsupported language: {language}. Supported languages: {', '.join(self.supported_languages)}")
            
            # Normalize language name
            language = next(lang for lang in self.supported_languages if lang.lower() == language.lower())
            
            if command == "generate":
                result = await self._generate_code(
                    language=language,
                    description=description,
                    template_type=template_type,
                    template_params=template_params
                )
                return result
            
            elif command == "validate":
                if not code:
                    return ToolResult(error="Code is required for validation")
                
                result = await self._validate_code(
                    language=language,
                    code=code
                )
                return result
            
            elif command == "test":
                if not code:
                    return ToolResult(error="Code is required for testing")
                
                result = await self._test_code(
                    language=language,
                    code=code,
                    test_input=test_input
                )
                return result
            
            elif command == "document":
                if not code:
                    return ToolResult(error="Code is required for documentation")
                
                result = await self._document_code(
                    language=language,
                    code=code
                )
                return result
            
            elif command == "explain":
                if not code:
                    return ToolResult(error="Code is required for explanation")
                
                result = await self._explain_code(
                    language=language,
                    code=code
                )
                return result
            
            else:
                return ToolResult(error=f"Unknown command: {command}. Supported commands: generate, validate, test, document, explain")
        
        except Exception as e:
            logger.error(f"Error in CodeGenerationTool: {str(e)}")
            return ToolResult(error=f"Error executing code generation: {str(e)}")
    
    async def _generate_code(
        self,
        language: str,
        description: str,
        template_type: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Generate code based on a natural language description.
        
        Args:
            language: The programming language to use
            description: Natural language description of the code to generate
            template_type: Optional template type to use
            template_params: Optional parameters for the template
            
        Returns:
            ToolResult with generated code
        """
        try:
            # If a template is specified, use it
            if template_type and template_params:
                if language not in self.templates or template_type not in self.templates[language]:
                    return ToolResult(error=f"Template '{template_type}' not found for language '{language}'")
                
                # Get the template
                template = self.templates[language][template_type]
                
                # Fill in the template
                code = template.format(**template_params)
            else:
                # Generate code using the LLM
                create_chat_completion = self.get_tool("create_chat_completion")
                if not create_chat_completion:
                    return ToolResult(error="create_chat_completion tool not available")
                
                # Prepare the prompt
                prompt = f"""
                Generate {language} code based on the following description:
                
                {description}
                
                Please provide only the code without any explanations or markdown formatting.
                """
                
                # Generate the code
                result = await create_chat_completion.execute(
                    messages=[{"role": "user", "content": prompt}]
                )
                
                if result.error:
                    return ToolResult(error=f"Error generating code: {result.error}")
                
                # Extract the code from the response
                response = json.loads(result.output)
                code = response["choices"][0]["message"]["content"]
                
                # Clean up the code (remove markdown code blocks if present)
                code = re.sub(r'^```\w*\n', '', code)
                code = re.sub(r'\n```$', '', code)
            
            # Validate the generated code
            validation_result = await self._validate_code(language, code)
            
            if validation_result.error:
                return ToolResult(
                    output=json.dumps({
                        "code": code,
                        "validation": {
                            "success": False,
                            "error": validation_result.error
                        }
                    })
                )
            else:
                return ToolResult(
                    output=json.dumps({
                        "code": code,
                        "validation": {
                            "success": True,
                            "message": validation_result.output
                        }
                    })
                )
        
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            return ToolResult(error=f"Error generating code: {str(e)}")
    
    async def _validate_code(
        self,
        language: str,
        code: str
    ) -> ToolResult:
        """
        Validate code with syntax checking.
        
        Args:
            language: The programming language of the code
            code: The code to validate
            
        Returns:
            ToolResult with validation result
        """
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(suffix=self._get_file_extension(language), mode='w', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Validate the code using language-specific tools
                if language == "python":
                    # Use Python's built-in compile function to check syntax
                    compile(code, '<string>', 'exec')
                    return ToolResult(output="Code syntax is valid")
                
                elif language in ["javascript", "typescript"]:
                    # Use the sandbox to run a syntax check
                    validation_code = f"""
                    try {{
                        eval("(() => {{ {code} }})()");
                        console.log("Code syntax is valid");
                    }} catch (error) {{
                        console.error("Syntax error: " + error.message);
                        process.exit(1);
                    }}
                    """
                    
                    result = await self.code_sandbox.execute_code(
                        validation_code,
                        language="javascript",
                        timeout=5
                    )
                    
                    if result.exit_code == 0:
                        return ToolResult(output="Code syntax is valid")
                    else:
                        return ToolResult(error=f"Syntax error: {result.stderr}")
                
                else:
                    # For other languages, we'll need to implement specific validation logic
                    # For now, return a message indicating that validation is not supported
                    return ToolResult(output=f"Syntax validation not implemented for {language}. Assuming code is valid.")
            
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error validating code: {str(e)}")
            return ToolResult(error=f"Syntax error: {str(e)}")
    
    async def _test_code(
        self,
        language: str,
        code: str,
        test_input: Optional[str] = None
    ) -> ToolResult:
        """
        Test code in a sandbox environment.
        
        Args:
            language: The programming language of the code
            code: The code to test
            test_input: Optional input for testing the code
            
        Returns:
            ToolResult with test result
        """
        try:
            # Prepare the code for testing
            test_code = code
            
            # If test input is provided, add it to the code
            if test_input:
                if language == "python":
                    test_code = f"{code}\n\n# Test code\n{test_input}"
                elif language in ["javascript", "typescript"]:
                    test_code = f"{code}\n\n// Test code\n{test_input}"
                else:
                    # For other languages, we'll need to implement specific testing logic
                    test_code = f"{code}\n\n{test_input}"
            
            # Execute the code in the sandbox
            result = await self.code_sandbox.execute_code(
                test_code,
                language=language,
                timeout=10
            )
            
            # Return the test result
            if result.exit_code == 0:
                return ToolResult(
                    output=json.dumps({
                        "success": True,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_time": result.execution_time
                    })
                )
            else:
                return ToolResult(
                    error=json.dumps({
                        "success": False,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_time": result.execution_time,
                        "exit_code": result.exit_code
                    })
                )
        
        except Exception as e:
            logger.error(f"Error testing code: {str(e)}")
            return ToolResult(error=f"Error testing code: {str(e)}")
    
    async def _document_code(
        self,
        language: str,
        code: str
    ) -> ToolResult:
        """
        Generate documentation for code.
        
        Args:
            language: The programming language of the code
            code: The code to document
            
        Returns:
            ToolResult with documentation
        """
        try:
            # Use the LLM to generate documentation
            create_chat_completion = self.get_tool("create_chat_completion")
            if not create_chat_completion:
                return ToolResult(error="create_chat_completion tool not available")
            
            # Prepare the prompt
            prompt = f"""
            Generate comprehensive documentation for the following {language} code:
            
            ```{language}
            {code}
            ```
            
            Please include:
            1. A high-level overview of what the code does
            2. Detailed explanations of functions, classes, and methods
            3. Parameter descriptions
            4. Return value descriptions
            5. Usage examples
            
            Format the documentation in Markdown.
            """
            
            # Generate the documentation
            result = await create_chat_completion.execute(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if result.error:
                return ToolResult(error=f"Error generating documentation: {result.error}")
            
            # Extract the documentation from the response
            response = json.loads(result.output)
            documentation = response["choices"][0]["message"]["content"]
            
            return ToolResult(output=documentation)
        
        except Exception as e:
            logger.error(f"Error documenting code: {str(e)}")
            return ToolResult(error=f"Error documenting code: {str(e)}")
    
    async def _explain_code(
        self,
        language: str,
        code: str
    ) -> ToolResult:
        """
        Explain code in natural language.
        
        Args:
            language: The programming language of the code
            code: The code to explain
            
        Returns:
            ToolResult with explanation
        """
        try:
            # Use the LLM to explain the code
            create_chat_completion = self.get_tool("create_chat_completion")
            if not create_chat_completion:
                return ToolResult(error="create_chat_completion tool not available")
            
            # Prepare the prompt
            prompt = f"""
            Explain the following {language} code in simple, natural language:
            
            ```{language}
            {code}
            ```
            
            Please provide:
            1. A high-level explanation of what the code does
            2. A step-by-step breakdown of how it works
            3. Any potential issues or improvements
            
            Make the explanation accessible to someone with basic programming knowledge.
            """
            
            # Generate the explanation
            result = await create_chat_completion.execute(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if result.error:
                return ToolResult(error=f"Error generating explanation: {result.error}")
            
            # Extract the explanation from the response
            response = json.loads(result.output)
            explanation = response["choices"][0]["message"]["content"]
            
            return ToolResult(output=explanation)
        
        except Exception as e:
            logger.error(f"Error explaining code: {str(e)}")
            return ToolResult(error=f"Error explaining code: {str(e)}")
    
    def _get_file_extension(self, language: str) -> str:
        """
        Get the file extension for a language.
        
        Args:
            language: The programming language
            
        Returns:
            File extension for the language
        """
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "c#": ".cs",
            "go": ".go",
            "rust": ".rs",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
            "bash": ".sh",
            "powershell": ".ps1"
        }
        
        return extensions.get(language.lower(), ".txt")
