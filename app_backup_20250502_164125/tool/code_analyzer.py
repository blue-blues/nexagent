import ast
import re
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.logger import logger


class CodeAnalyzer(BaseTool):
    """
    A tool for analyzing code, detecting bugs, suggesting optimizations,
    and providing architectural recommendations.
    """

    name: str = "code_analyzer"
    description: str = """
    Analyzes code to detect bugs, suggest optimizations, and provide architectural recommendations.
    Supports multiple programming languages including Python, JavaScript, Java, and more.
    
    Commands:
    - analyze_code: Analyze code for bugs, style issues, and optimization opportunities
    - suggest_architecture: Suggest architectural patterns based on project requirements
    - detect_language: Automatically detect the programming language of a code snippet
    - explain_error: Analyze and explain error messages with suggested fixes
    - suggest_tests: Generate test cases for the provided code
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": [
                    "analyze_code", 
                    "suggest_architecture", 
                    "detect_language", 
                    "explain_error",
                    "suggest_tests"
                ],
                "description": "The analysis command to perform"
            },
            "code": {
                "type": "string",
                "description": "The code snippet to analyze"
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file containing code to analyze"
            },
            "language": {
                "type": "string",
                "description": "Programming language of the code (auto-detected if not provided)"
            },
            "error_message": {
                "type": "string",
                "description": "Error message to analyze and explain"
            },
            "project_requirements": {
                "type": "string",
                "description": "Project requirements for architecture suggestions"
            }
        },
        "required": ["command"]
    }
    
    async def execute(
        self,
        *,
        command: str,
        code: Optional[str] = None,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        error_message: Optional[str] = None,
        project_requirements: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Execute the code analysis tool with the specified command."""
        
        try:
            if command == "analyze_code":
                if not code and not file_path:
                    return ToolResult(error="Either code or file_path must be provided")
                
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception as e:
                        return ToolResult(error=f"Failed to read file: {str(e)}")
                
                if not language:
                    language = self._detect_language(code)
                
                analysis_result = self._analyze_code(code, language)
                return ToolResult(output=json.dumps(analysis_result, indent=2))
            
            elif command == "suggest_architecture":
                if not project_requirements:
                    return ToolResult(error="Project requirements must be provided")
                
                architecture_suggestions = self._suggest_architecture(project_requirements)
                return ToolResult(output=json.dumps(architecture_suggestions, indent=2))
            
            elif command == "detect_language":
                if not code and not file_path:
                    return ToolResult(error="Either code or file_path must be provided")
                
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception as e:
                        return ToolResult(error=f"Failed to read file: {str(e)}")
                
                detected_language = self._detect_language(code)
                return ToolResult(output=f"Detected language: {detected_language}")
            
            elif command == "explain_error":
                if not error_message:
                    return ToolResult(error="Error message must be provided")
                
                explanation = self._explain_error(error_message, language, code)
                return ToolResult(output=json.dumps(explanation, indent=2))
            
            elif command == "suggest_tests":
                if not code and not file_path:
                    return ToolResult(error="Either code or file_path must be provided")
                
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception as e:
                        return ToolResult(error=f"Failed to read file: {str(e)}")
                
                if not language:
                    language = self._detect_language(code)
                
                test_suggestions = self._suggest_tests(code, language)
                return ToolResult(output=json.dumps(test_suggestions, indent=2))
            
            else:
                return ToolResult(error=f"Unknown command: {command}")
        
        except Exception as e:
            logger.error(f"Error in CodeAnalyzer: {str(e)}")
            return ToolResult(error=f"Analysis failed: {str(e)}")
    
    def _detect_language(self, code: str) -> str:
        """Detect the programming language of a code snippet."""
        # Check for Python syntax
        if re.search(r'def\s+\w+\s*\(.*\)\s*:', code) or \
           re.search(r'import\s+[\w\.]+', code) or \
           re.search(r'from\s+[\w\.]+\s+import', code):
            return "python"
        
        # Check for JavaScript/TypeScript syntax
        if re.search(r'function\s+\w+\s*\(.*\)\s*\{', code) or \
           re.search(r'const\s+\w+\s*=', code) or \
           re.search(r'let\s+\w+\s*=', code) or \
           re.search(r'var\s+\w+\s*=', code) or \
           re.search(r'=>\s*\{', code):
            if re.search(r':\s*[A-Za-z\[\]\{\}]+\s*[,;=)]', code):
                return "typescript"
            return "javascript"
        
        # Check for Java syntax
        if re.search(r'public\s+class\s+\w+', code) or \
           re.search(r'private\s+\w+\s+\w+\s*;', code) or \
           re.search(r'import\s+java\.', code):
            return "java"
        
        # Check for C/C++ syntax
        if re.search(r'#include\s*<[\w\.]+>', code) or \
           re.search(r'int\s+main\s*\(', code):
            if re.search(r'std::', code) or re.search(r'template\s*<', code):
                return "c++"
            return "c"
        
        # Check for HTML
        if re.search(r'<!DOCTYPE\s+html>', code, re.IGNORECASE) or \
           re.search(r'<html[\s>]', code, re.IGNORECASE):
            return "html"
        
        # Check for CSS
        if re.search(r'[\w-]+\s*\{[^}]*\}', code) and \
           re.search(r'[\w-]+\s*:\s*[^;]+;', code):
            return "css"
        
        # Default to unknown
        return "unknown"
    
    def _analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for bugs, style issues, and optimization opportunities."""
        result = {
            "language": language,
            "issues": [],
            "optimizations": [],
            "style_suggestions": [],
            "security_concerns": []
        }
        
        if language == "python":
            self._analyze_python_code(code, result)
        elif language in ["javascript", "typescript"]:
            self._analyze_js_ts_code(code, result)
        elif language == "java":
            self._analyze_java_code(code, result)
        elif language in ["c", "c++"]:
            self._analyze_c_cpp_code(code, result)
        elif language == "html":
            self._analyze_html_code(code, result)
        elif language == "css":
            self._analyze_css_code(code, result)
        
        return result
    
    def _analyze_python_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze Python code for issues."""
        # Check for common Python issues
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Check for unused imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        imports.append(name.name)
            
            # Check for bare excepts
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    result["issues"].append({
                        "type": "bare_except",
                        "message": "Bare 'except:' detected. Specify exception types to catch.",
                        "line": node.lineno
                    })
            
            # Check for mutable default arguments
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for arg in node.args.defaults:
                        if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                            result["issues"].append({
                                "type": "mutable_default",
                                "message": f"Mutable default argument in function '{node.name}'. Use None as default instead.",
                                "line": node.lineno
                            })
        except SyntaxError as e:
            result["issues"].append({
                "type": "syntax_error",
                "message": f"Syntax error: {str(e)}",
                "line": e.lineno if hasattr(e, 'lineno') else None
            })
        
        # Check for security issues
        if "eval(" in code:
            result["security_concerns"].append({
                "type": "eval_usage",
                "message": "Use of eval() detected, which can be a security risk."
            })
        
        if "exec(" in code:
            result["security_concerns"].append({
                "type": "exec_usage",
                "message": "Use of exec() detected, which can be a security risk."
            })
        
        # Style checks
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if len(line) > 100:
                result["style_suggestions"].append({
                    "type": "line_length",
                    "message": "Line exceeds 100 characters. Consider breaking it up.",
                    "line": i + 1
                })
    
    def _analyze_js_ts_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze JavaScript/TypeScript code for issues."""
        # Check for common JS/TS issues
        if "==" in code:
            result["issues"].append({
                "type": "loose_equality",
                "message": "Use of loose equality (==) detected. Consider using strict equality (===) instead."
            })
        
        # Check for console.log statements
        console_logs = re.findall(r'console\.log\(', code)
        if console_logs:
            result["style_suggestions"].append({
                "type": "console_log",
                "message": f"Found {len(console_logs)} console.log statements. Consider removing them in production code."
            })
        
        # Check for security issues
        if "eval(" in code:
            result["security_concerns"].append({
                "type": "eval_usage",
                "message": "Use of eval() detected, which can be a security risk."
            })
        
        if "innerHTML" in code:
            result["security_concerns"].append({
                "type": "innerHTML",
                "message": "Use of innerHTML detected, which can lead to XSS vulnerabilities. Consider using textContent or DOM methods instead."
            })
    
    def _analyze_java_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze Java code for issues."""
        # Check for common Java issues
        if "System.out.println" in code:
            result["style_suggestions"].append({
                "type": "println",
                "message": "Use of System.out.println detected. Consider using a logging framework instead."
            })
        
        # Check for potential null pointer exceptions
        if re.search(r'\w+\.\w+\(\)', code) and not re.search(r'if\s*\(\s*\w+\s*!=\s*null\s*\)', code):
            result["issues"].append({
                "type": "null_check",
                "message": "Potential null pointer exception. Consider adding null checks."
            })
    
    def _analyze_c_cpp_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze C/C++ code for issues."""
        # Check for common C/C++ issues
        if "malloc(" in code and "free(" not in code:
            result["issues"].append({
                "type": "memory_leak",
                "message": "Potential memory leak: malloc() used without corresponding free()."
            })
        
        if "strcpy(" in code:
            result["security_concerns"].append({
                "type": "buffer_overflow",
                "message": "Use of strcpy() detected, which can lead to buffer overflow. Consider using strncpy() or strlcpy() instead."
            })
        
        # Check for array bounds
        if re.search(r'\[\w+\]', code) and not re.search(r'if\s*\(\s*\w+\s*<\s*\w+\s*\)', code):
            result["issues"].append({
                "type": "array_bounds",
                "message": "Potential array bounds issue. Consider adding bounds checking."
            })
    
    def _analyze_html_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze HTML code for issues."""
        # Check for common HTML issues
        if "<img" in code and not re.search(r'<img[^>]*alt=["\'][^"\'>]*["\']', code):
            result["issues"].append({
                "type": "accessibility",
                "message": "Image without alt attribute. Add alt attributes for accessibility."
            })
        
        if "<a" in code and not re.search(r'<a[^>]*href=["\'][^"\'>]*["\']', code):
            result["issues"].append({
                "type": "link_issue",
                "message": "Anchor tag without href attribute."
            })
    
    def _analyze_css_code(self, code: str, result: Dict[str, Any]) -> None:
        """Analyze CSS code for issues."""
        # Check for common CSS issues
        if "!important" in code:
            result["style_suggestions"].append({
                "type": "important_usage",
                "message": "Use of !important detected. Consider using more specific selectors instead."
            })
        
        # Check for browser-specific prefixes without standard property
        prefixes = ["-webkit-", "-moz-", "-ms-", "-o-"]
        for prefix in prefixes:
            if prefix in code:
                result["style_suggestions"].append({
                    "type": "vendor_prefix",
                    "message": f"Use of {prefix} vendor prefix detected. Consider adding standard property as well."
                })
    
    def _suggest_architecture(self, project_requirements: str) -> Dict[str, Any]:
        """Suggest architectural patterns based on project requirements."""
        suggestions = {
            "architecture_patterns": [],
            "component_breakdown": [],
            "technology_stack": [],
            "database_recommendations": [],
            "api_design": []
        }
        
        # Detect web application requirements
        if any(term in project_requirements.lower() for term in ["web", "website", "frontend", "backend", "http", "api"]):
            suggestions["architecture_patterns"].append({
                "name": "MVC (Model-View-Controller)",
                "description": "Separates application into three components: Model (data), View (UI), and Controller (business logic).",
                "suitability": "High for web applications with user interfaces"
            })
            
            suggestions["architecture_patterns"].append({
                "name": "Microservices",
                "description": "Breaks application into small, independent services that communicate via APIs.",
                "suitability": "High for complex, scalable applications"
            })
            
            # Suggest component breakdown for web apps
            suggestions["component_breakdown"] = [
                "Authentication Service",
                "API Gateway",
                "Frontend UI Components",
                "Backend Services",
                "Database Layer",
                "Caching Layer"
            ]
        
        # Detect data processing requirements
        if any(term in project_requirements.lower() for term in ["data", "analytics", "processing", "etl", "pipeline"]):
            suggestions["architecture_patterns"].append({
                "name": "ETL (Extract, Transform, Load)",
                "description": "Pattern for extracting data from sources, transforming it, and loading into target systems.",
                "suitability": "High for data processing applications"
            })
            
            suggestions["architecture_patterns"].append({
                "name": "Lambda Architecture",
                "description": "Combines batch and stream processing for data analysis.",
                "suitability": "High for big data applications with real-time requirements"
            })
            
            # Suggest component breakdown for data apps
            suggestions["component_breakdown"] = [
                "Data Ingestion Layer",
                "Data Storage Layer",
                "Processing Engine",
                "Analytics Service",
                "Visualization Components"
            ]
        
        # Detect mobile application requirements
        if any(term in project_requirements.lower() for term in ["mobile", "android", "ios", "app"]):
            suggestions["architecture_patterns"].append({
                "name": "MVVM (Model-View-ViewModel)",
                "description": "Separates UI from business logic and provides better testability.",
                "suitability": "High for mobile applications"
            })
            
            # Suggest component breakdown for mobile apps
            suggestions["component_breakdown"] = [
                "UI Layer",
                "Business Logic Layer",
                "Data Access Layer",
                "Network Service",
                "Local Storage"
            ]
        
        # Suggest technology stack based on requirements
        if "python" in project_requirements.lower():
            suggestions["technology_stack"].append({
                "category": "Backend",
                "options": ["Django", "Flask", "FastAPI"]
            })
        
        if "javascript" in project_requirements.lower() or "web" in project_requirements.lower():
            suggestions["technology_stack"].append({
                "category": "Frontend",
                "options": ["React", "Vue.js", "Angular"]
            })
        
        # Default technology suggestions if none specified
        if not suggestions["technology_stack"]:
            suggestions["technology_stack"] = [
                {
                    "category": "Backend",
                    "options": ["Node.js", "Python (Django/Flask)", "Java (Spring Boot)"]
                },
                {
                    "category": "Frontend",
                    "options": ["React", "Vue.js", "Angular"]
                },
                {
                    "category": "Database",
                    "options": ["PostgreSQL", "MongoDB", "MySQL"]
                }
            ]
        
        # Database recommendations
        if "relational" in project_requirements.lower() or "sql" in project_requirements.lower():
            suggestions["database_recommendations"].append({
                "type": "Relational",
                "options": ["PostgreSQL", "MySQL", "SQLite"]
            })
        elif "nosql" in project_requirements.lower() or "document" in project_requirements.lower():
            suggestions["database_recommendations"].append({
                "type": "NoSQL",
                "options": ["MongoDB", "Cassandra", "DynamoDB"]
            })
        else:
            suggestions["database_recommendations"].append({
                "type": "General",
                "options": ["PostgreSQL", "MongoDB", "SQLite"]
            })
        
        return suggestions
    
    def _explain_error(self, error_message: str, language: Optional[str] = None, code: Optional[str] = None) -> Dict[str, Any]:
        """Analyze and explain error messages with suggested fixes."""
        explanation = {
            "error_type": "unknown",
            "explanation": "",
            "possible_causes": [],
            "suggested_fixes": []
        }
        
        # Python errors
        if "SyntaxError" in error_message:
            explanation["error_type"] = "SyntaxError"
            explanation["explanation"] = "Python syntax error: The code contains invalid syntax."
            explanation["possible_causes"] = [
                "Missing parentheses, brackets, or quotes",
                "Invalid indentation",
                "Missing colons after if/for/while statements"
            ]
            explanation["suggested_fixes"] = [
                "Check for missing parentheses or brackets",
                "Ensure proper indentation (4 spaces per level is standard in Python)",
                "Add required colons after control flow statements"
            ]
        
        elif "IndentationError" in error_message:
            explanation["error_type"] = "IndentationError"
            explanation["explanation"] = "Python indentation error: Inconsistent use of tabs and spaces."
            explanation["possible_causes"] = [
                "Mixing tabs and spaces",
                "Inconsistent indentation levels"
            ]
            explanation["suggested_fixes"] = [
                "Use either tabs or spaces consistently (preferably 4 spaces)",
                "Check for lines with incorrect indentation"
            ]
        
        elif "NameError" in error_message:
            explanation["error_type"] = "NameError"
            explanation["explanation"] = "Python name error: Attempting to use a variable or function that doesn't exist."
            explanation["possible_causes"] = [
                "Typo in variable or function name",
                "Using a variable before it's defined",
                "Missing import statement"
            ]
            explanation["suggested_fixes"] = [
                "Check for typos in variable names",
                "Ensure variables are defined before use",
                "Add necessary import statements"
            ]
        
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            explanation["error_type"] = "ImportError"
            explanation["explanation"] = "Python import error: Unable to import a module or package."
            explanation["possible_causes"] = [
                "Module is not installed",
                "Typo in module name",
                "Module is not in the Python path"
            ]
            
            # Extract module name if available
            module_match = re.search(r"No module named '([\w\.]+)'", error_message)
            if module_match:
                module_name = module_match.group(1)
                explanation["suggested_fixes"] = [
                    f"Install the module: pip install {module_name}",
                    "Check for typos in the import statement",
                    "Ensure the module is in your Python path"
                ]
            else:
                explanation["suggested_fixes"] = [
                    "Install the required module using pip",
                    "Check for typos in the import statement",
                    "Ensure the module is in your Python path"
                ]
        
        # JavaScript errors
        elif "ReferenceError" in error_message and (language == "javascript" or language == "typescript"):
            explanation["error_type"] = "ReferenceError"
            explanation["explanation"] = "JavaScript reference error: Attempting to use a variable that doesn't exist."
            explanation["possible_causes"] = [
                "Typo in variable name",
                "Using a variable before it's defined",
                "Variable is out of scope"
            ]
            explanation["suggested_fixes"] = [
                "Check for typos in variable names",
                "Ensure variables are defined before use",
                "Check variable scope and closures"
            ]
        
        elif "TypeError" in error_message:
            explanation["error_type"] = "TypeError"
            explanation["explanation"] = "Type error: Operation performed on an incompatible type."
            explanation["possible_causes"] = [
                "Calling a non-function",
                "Passing incorrect argument types to a function",
                "Performing operations on incompatible types"
            ]
            explanation["suggested_fixes"] = [
                "Check the types of variables being used",
                "Ensure function arguments match expected types",
                "Add type conversion if necessary"
            ]
        
        # Generic error handling if specific patterns not found
        else:
            explanation["explanation"] = f"Unrecognized error: {error_message}"
            explanation["possible_causes"] = ["Unknown cause"]
            explanation["suggested_fixes"] = ["Review the error message carefully and check documentation"]
        
        return explanation
    
    def _suggest_tests(self, code: str, language: str) -> Dict[str, Any]:
        """Generate test case suggestions for the provided code."""
        test_suggestions = {
            "language": language,
            "test_framework": "",
            "unit_tests": [],
            "integration_tests": [],
            "edge_cases": []
        }
        
        # Python test suggestions
        if language == "python":
            test_suggestions["test_framework"] = "pytest"
            
            # Parse the code to extract functions and classes
            try:
                tree = ast.parse(code)
                
                # Extract function definitions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        function_name = node.name
                        args = [arg.arg for arg in node.args.args]
                        
                        # Skip test functions and private methods
                        if function_name.startswith("test_") or function_name.startswith("_"):
                            continue
                        
                        # Generate test case for this function
                        test_case = {
                            "function_name": function_name,
                            "test_name": f"test_{function_name}",
                            "parameters": args,
                            "test_cases": [
                                {
                                    "description": f"Test {function_name} with valid input",
                                    "input": {arg: f"<{arg}_value>" for arg in args},
                                    "expected_output": "<expected_output>"
                                },
                                {
                                    "description": f"Test {function_name} with edge case",
                                    "input": {arg: f"<{arg}_edge_value>" for arg in args},
                                    "expected_output": "<expected_output_for_edge_case>"
                                }
                            ],
                            "mock_dependencies": []
                        }
                        
                        # Look for potential dependencies to mock
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                                for name in node.names:
                                    if name.name not in ["os", "sys", "re", "math", "datetime", "collections"]:
                                        if name.name not in [dep for dep in test_case["mock_dependencies"]]:
                                            test_case["mock_dependencies"].append(name.name)
                        
                        test_suggestions["unit_tests"].append(test_case)
                
                # Generate example test code
                test_code_examples = []
                for test in test_suggestions["unit_tests"][:2]:  # Generate examples for first 2 tests
                    test_code = f"""def {test['test_name']}():\n"""
                    
                    # Add mocks if needed
                    if test["mock_dependencies"]:
                        test_code += "    # Setup mocks\n"
                        for dep in test["mock_dependencies"]:
                            test_code += f"    with patch('{dep}') as mock_{dep.lower()}:\n"
                        test_code += "\n"
                    
                    # Add test case implementation
                    for i, case in enumerate(test["test_cases"]):
                        test_code += f"    # {case['description']}\n"
                        args_str = ", ".join([f"{k}={v}" for k, v in case["input"].items()])
                        test_code += f"    result = {test['function_name']}({args_str})\n"
                        test_code += f"    assert result == {case['expected_output']}\n\n"
                    
                    test_code_examples.append(test_code)
                
                test_suggestions["example_test_code"] = test_code_examples
            
            except SyntaxError as e:
                test_suggestions["unit_tests"].append({
                    "error": f"Could not parse code: {str(e)}"
                })
        
        # JavaScript test suggestions
        elif language in ["javascript", "typescript"]:
            test_suggestions["test_framework"] = "jest"
            
            # Extract function definitions using regex
            function_defs = re.findall(r'function\s+(\w+)\s*\(([^)]*)\)', code)
            arrow_funcs = re.findall(r'const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>', code)
            
            # Combine both types of functions
            all_funcs = function_defs + arrow_funcs
            
            for func_name, params in all_funcs:
                # Skip test functions
                if func_name.startswith("test") or func_name.startswith("_"):
                    continue
                
                # Parse parameters
                param_list = [p.strip().split(':')[0].strip() for p in params.split(',') if p.strip()]
                
                test_case = {
                    "function_name": func_name,
                    "test_name": f"test{func_name.capitalize()}",
                    "parameters": param_list,
                    "test_cases": [
                        {
                            "description": f"should correctly handle valid input for {func_name}",
                            "input": {param: f"<{param}_value>" for param in param_list},
                            "expected_output": "<expected_output>"
                        },
                        {
                            "description": f"should handle edge cases for {func_name}",
                            "input": {param: f"<{param}_edge_value>" for param in param_list},
                            "expected_output": "<expected_output_for_edge_case>"
                        }
                    ],
                    "mock_dependencies": []
                }
                
                # Look for potential dependencies to mock
                imports = re.findall(r'import\s+\{([^}]+)\}\s+from\s+["\'](.*?)["\'](;?)', code)
                for import_match in imports:
                    modules = [m.strip() for m in import_match[0].split(',')]
                    for module in modules:
                        if module not in test_case["mock_dependencies"]:
                            test_case["mock_dependencies"].append(module)
                
                test_suggestions["unit_tests"].append(test_case)
            
            # Generate example test code
            test_code_examples = []
            for test in test_suggestions["unit_tests"][:2]:  # Generate examples for first 2 tests
                test_code = f"""describe('{test['function_name']}', () => {{\n"""
                
                # Add mocks if needed
                if test["mock_dependencies"]:
                    test_code += "  // Setup mocks\n"
                    for dep in test["mock_dependencies"]:
                        test_code += f"  jest.mock('{dep}');\n"
                    test_code += "\n"
                
                # Add test case implementation
                for i, case in enumerate(test["test_cases"]):
                    test_code += f"  test('{case['description']}', () => {{\n"
                    args_str = ", ".join([f"{v}" for k, v in case["input"].items()])
                    test_code += f"    const result = {test['function_name']}({args_str});\n"
                    test_code += f"    expect(result).toEqual({case['expected_output']});\n"
                    test_code += "  });\n\n"
                
                test_code += "});\n"
                test_code_examples.append(test_code)
            
            test_suggestions["example_test_code"] = test_code_examples
        
        # Java test suggestions
        elif language == "java":
            test_suggestions["test_framework"] = "JUnit"
            
            # Extract class and method definitions using regex
            class_defs = re.findall(r'(public|private)\s+class\s+(\w+)', code)
            method_defs = re.findall(r'(public|private|protected)\s+(?:static\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)', code)
            
            for access, return_type, method_name, params in method_defs:
                # Skip test methods
                if method_name.startswith("test") or method_name.startswith("_"):
                    continue
                
                # Parse parameters
                param_list = []
                if params.strip():
                    for param in params.split(','):
                        parts = param.strip().split()
                        if len(parts) >= 2:
                            param_list.append(parts[-1])  # Get parameter name
                
                test_case = {
                    "method_name": method_name,
                    "test_name": f"test{method_name.capitalize()}",
                    "return_type": return_type,
                    "parameters": param_list,
                    "test_cases": [
                        {
                            "description": f"Test {method_name} with valid input",
                            "input": {param: f"<{param}_value>" for param in param_list},
                            "expected_output": "<expected_output>"
                        },
                        {
                            "description": f"Test {method_name} with edge case",
                            "input": {param: f"<{param}_edge_value>" for param in param_list},
                            "expected_output": "<expected_output_for_edge_case>"
                        }
                    ],
                    "mock_dependencies": []
                }
                
                test_suggestions["unit_tests"].append(test_case)
        
        # Add integration test suggestions if multiple functions/classes detected
        if len(test_suggestions["unit_tests"]) > 1:
            test_suggestions["integration_tests"] = [
                {
                    "description": "Test the interaction between components",
                    "components_involved": [test["function_name" if "function_name" in test else "method_name"] 
                                          for test in test_suggestions["unit_tests"][:2]],
                    "test_scenario": "Verify that the components work correctly together"
                }
            ]
        
        # Add edge case suggestions
        test_suggestions["edge_cases"] = [
            "Test with empty input",
            "Test with very large input",
            "Test with invalid input",
            "Test with boundary values",
            "Test with null/None values"
        ]
        
        return test_suggestions