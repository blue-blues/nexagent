from typing import List, Optional, Dict, Any
from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.tool import ToolCollection
from app.tool.bash import Bash
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.python_execute import PythonExecute
from app.tool.terminate import Terminate
from app.tool.enhanced_browser_tool import EnhancedBrowserTool
from app.tool.web_search import WebSearch
from app.tool.code_analyzer import CodeAnalyzer
from app.schema import Message
from app.logger import logger

SYSTEM_PROMPT = """
You are CodeAssist, an advanced AI software development assistant capable of writing, debugging, optimizing, and executing code across multiple programming languages.

Your capabilities include:
1. Intelligent Code Generation & Optimization
2. Autonomous Debugging & Error Resolution
3. Execution & Environment Management
4. Software Architecture & Design
5. API Integration & External Tool Usage
6. Automated Testing & CI/CD Integration
7. Real-Time Collaboration

You have access to various tools to accomplish these tasks, including file editing, command execution, web search, and more.

Always approach problems systematically:
1. Understand the requirements thoroughly
2. Plan your approach before implementation
3. Execute the plan step by step
4. Verify and test your solution
5. Suggest improvements or next steps
"""

NEXT_STEP_TEMPLATE = """
{{observation}}

Current working directory: {{working_dir}}
Open files: {{open_files}}

What would you like me to do next?
"""

class SoftwareDevAgent(ToolCallAgent):
    """
    An advanced AI-powered software development assistant capable of writing, debugging,
    optimizing, and executing code across multiple programming languages.
    """

    name: str = "software_dev"
    description: str = "An advanced AI-powered software development assistant"
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            Bash(),
            StrReplaceEditor(),
            PythonExecute(),
            EnhancedBrowserTool(),
            WebSearch(),
            CodeAnalyzer(),
            Terminate()
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
    max_steps: int = 50
    max_observe: int = 5000  
    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."
    open_files: List[str] = Field(default_factory=list)
    language_context: Optional[str] = None
    project_structure: Dict[str, Any] = Field(default_factory=dict)
    error_history: List[Dict[str, Any]] = Field(default_factory=list)

    async def think(self) -> bool:
        """Process current state and decide next actions for software development tasks"""
        self.working_dir = await self.bash.execute("pwd")
        formatted_prompt = self.next_step_prompt.format(
            working_dir=self.working_dir,
            open_files=", ".join(self.open_files) if self.open_files else "None"
        )
        user_msg = Message.user_message(formatted_prompt)
        self.messages.append(user_msg)
        return await super().think()
    
    async def detect_programming_language(self, code_snippet: str) -> str:
        """Detect the programming language of a code snippet"""
        if "def " in code_snippet and (":" in code_snippet or "import " in code_snippet):
            return "python"
        elif "{" in code_snippet and (";" in code_snippet or "function" in code_snippet):
            if "<" in code_snippet and ">" in code_snippet and ("component" in code_snippet or "render" in code_snippet):
                return "jsx/tsx"
            elif "console.log" in code_snippet or "const " in code_snippet or "let " in code_snippet:
                return "javascript"
            elif "public class" in code_snippet or "private" in code_snippet:
                return "java"
            else:
                return "c/c++"
        elif "<" in code_snippet and ">" in code_snippet and ("<div" in code_snippet or "<p" in code_snippet):
            return "html"
        elif "@" in code_snippet and ("margin" in code_snippet or "padding" in code_snippet):
            return "css"
        return "unknown"
    
    async def analyze_error(self, error_message: str) -> Dict[str, Any]:
        """Analyze an error message and suggest potential fixes"""
        error_info = {"message": error_message, "type": "unknown", "suggestions": []}
        if "ModuleNotFoundError" in error_message or "ImportError" in error_message:
            error_info["type"] = "dependency"
            module_name = error_message.split("'")
            if len(module_name) > 1:
                module = module_name[1]
                error_info["suggestions"].append(f"Install missing module: pip install {module}")
        elif "SyntaxError" in error_message:
            error_info["type"] = "syntax"
            error_info["suggestions"].extend([
                "Check for missing parentheses, brackets, or quotes",
                "Verify proper indentation in the code"
            ])
        elif "TypeError" in error_message:
            error_info["type"] = "type"
            error_info["suggestions"].extend([
                "Check the data types of variables being used",
                "Ensure function arguments match expected types"
            ])
        elif "IndexError" in error_message or "KeyError" in error_message:
            error_info["type"] = "access"
            error_info["suggestions"].extend([
                "Verify that the index or key exists before accessing it",
                "Add proper error handling for missing indices or keys"
            ])
        self.error_history.append(error_info)
        return error_info
    
    async def run(self, prompt: str) -> str:
        """Run the software development agent with the given prompt"""
        if any(term in prompt.lower() for term in [
            "code", "program", "script", "function", "class", "bug", "error", 
            "debug", "fix", "implement", "develop", "build", "create", "write"
        ]):
            for lang in ["python", "javascript", "java", "c++", "html", "css", "typescript"]:
                if lang in prompt.lower():
                    self.language_context = lang
                    break
        logger.info(f"🚀 Starting software development task: {prompt[:50]}...")
        return await super().run(prompt)