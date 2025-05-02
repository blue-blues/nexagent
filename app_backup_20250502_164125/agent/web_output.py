from typing import Any
import re
import json


class WebOutputFormatter:
    """Utility class for formatting agent output for web display.

    This class provides methods to clean, structure, and optimize agent output
    for better presentation in web interfaces.
    """

    @staticmethod
    def format_output(output: str, is_final_output: bool = False) -> str:
        """Format raw agent output for web display.

        Args:
            output: Raw output string from agent
            is_final_output: Whether this is the final output (not an intermediate step)

        Returns:
            Formatted output string optimized for web display
        """
        if not output:
            return ""

        # Remove excessive newlines
        formatted = re.sub(r'\n{3,}', '\n\n', output)

        # Format code blocks properly
        formatted = WebOutputFormatter._enhance_code_blocks(formatted)

        # Format lists for better display
        formatted = WebOutputFormatter._enhance_lists(formatted)

        # Format tables for better display
        formatted = WebOutputFormatter._enhance_tables(formatted)

        # Highlight important information
        formatted = WebOutputFormatter._highlight_important_info(formatted)

        # Structure sections with headers
        formatted = WebOutputFormatter._structure_sections(formatted)

        # Format JSON-like content that's not in code blocks
        formatted = WebOutputFormatter._format_inline_json(formatted)

        # Add special formatting for final output
        if is_final_output:
            # Check if there's already a final output section
            if not re.search(r'\n## Final Output|\n## Result|\n## Summary', formatted, re.IGNORECASE):
                # Add a clear separator and header for the final output
                formatted = f"\n\n---\n\n## Final Output\n\n{formatted}"

        return formatted

    @staticmethod
    def _enhance_code_blocks(text: str) -> str:
        """Enhance code blocks for better web display."""
        # Ensure code blocks have proper language tags and formatting
        pattern = r'```(\w*)\n([\s\S]*?)```'

        def replace_code_block(match):
            lang = match.group(1) or "text"
            code = match.group(2)

            # Trim trailing whitespace from each line
            code_lines = [line.rstrip() for line in code.split('\n')]

            # Ensure consistent indentation
            code = '\n'.join(code_lines)

            # Add syntax highlighting hint
            return f"```{lang}\n{code}\n```"

        return re.sub(pattern, replace_code_block, text)

    @staticmethod
    def _enhance_lists(text: str) -> str:
        """Enhance lists for better web display."""
        # Ensure proper spacing in lists
        text = re.sub(r'(\n- .*)(\n)(?!-|\n)', '\\1\\2\\n', text)

        # Improve nested list formatting
        text = re.sub(r'(\n\s*- .*)(\n)(?!\s*-|\n)', '\\1\\2\\n', text)

        # Add spacing after list sections
        text = re.sub(r'((?:\n\s*-[^\n]+)+\n)(?=\S)', '\\1\n', text)

        # Ensure consistent bullet points
        text = re.sub(r'\n\s*\*\s', '\n- ', text)
        text = re.sub(r'\n\s*•\s', '\n- ', text)

        return text

    @staticmethod
    def _highlight_important_info(text: str) -> str:
        """Highlight important information in the output."""
        # Highlight warnings and errors
        text = re.sub(r'(?i)(warning|error|caution|important|note|tip):\s*([^\n]+)', r'**\\1:** \\2', text)

        # Highlight key terms in parentheses
        text = re.sub(r'\(([^)]{3,30})\)', r'(**\\1**)', text)

        return text

    @staticmethod
    def _enhance_tables(text: str) -> str:
        """Enhance markdown tables for better display."""
        # Find markdown tables and ensure they have proper formatting
        table_pattern = r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+)'

        def format_table(match):
            table = match.group(1)
            # Ensure table has a blank line before and after
            if not table.startswith('\n'):
                table = '\n' + table
            if not table.endswith('\n\n'):
                table = table.rstrip('\n') + '\n\n'
            return table

        return re.sub(table_pattern, format_table, text)

    @staticmethod
    def _structure_sections(text: str) -> str:
        """Structure content into clear sections based on headers."""
        # Add spacing after headers
        text = re.sub(r'(\n#{1,6} .+)\n(?!\n)', '\\1\n\n', text)

        # Add horizontal rule before major sections (h1, h2)
        text = re.sub(r'\n(#{1,2} .+)\n', '\n\n---\n\\1\n', text)

        return text

    @staticmethod
    def _format_inline_json(text: str) -> str:
        """Format JSON-like content that's not in code blocks."""
        # Skip content inside code blocks
        parts = re.split(r'(```[\s\S]*?```)', text)
        result = []

        for i, part in enumerate(parts):
            # Skip code blocks (odd indices)
            if i % 2 == 1:
                result.append(part)
                continue

            # Look for JSON-like dictionary patterns and format them
            json_pattern = r'\{\s*"[^"]+"\s*:\s*[^{}\[\]]*(?:\{[^{}]*\}|\[[^\[\]]*\])*[^{}\[\]]*\}'

            def format_json_match(match):
                try:
                    json_str = match.group(0)
                    data = json.loads(json_str)
                    return f"```json\n{json.dumps(data, indent=2)}\n```"
                except:
                    return match.group(0)

            part = re.sub(json_pattern, format_json_match, part)
            result.append(part)

        return ''.join(result)

    @staticmethod
    def structure_tool_result(result: str) -> str:
        """Structure tool execution results for better readability.

        Args:
            result: Raw tool execution result

        Returns:
            Structured and formatted tool result
        """
        if not result:
            return ""

        # Try to parse JSON if the result is JSON
        try:
            data = json.loads(result)
            return WebOutputFormatter._format_json_result(data)
        except json.JSONDecodeError:
            pass

        # Format command output
        if result.startswith("Observed output of cmd"):
            return WebOutputFormatter._format_command_result(result)

        return result

    @staticmethod
    def _format_json_result(data: Any) -> str:
        """Format JSON data for better display."""
        try:
            # Format JSON with proper indentation and sorting
            formatted_json = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)

            # Add syntax highlighting
            return f"```json\n{formatted_json}\n```"
        except:
            return str(data)

    @staticmethod
    def _format_command_result(result: str) -> str:
        """Format command execution result for better display."""
        # Extract the command name and output
        match = re.match(r"Observed output of cmd `([^`]+)` executed:\n(.*)$", result, re.DOTALL)
        if not match:
            return result

        cmd_name = match.group(1)
        cmd_output = match.group(2)

        # Determine language for syntax highlighting based on command
        lang = "shell"
        if cmd_name.endswith(".py") or "python" in cmd_name:
            lang = "python"
        elif cmd_name.endswith(".js") or "node" in cmd_name:
            lang = "javascript"
        elif cmd_name.endswith(".ts"):
            lang = "typescript"

        # Format with proper syntax highlighting
        return f"### Command Execution: `{cmd_name}`\n\n```{lang}\n{cmd_output}\n```"

    @staticmethod
    def filter_technical_details(output: str) -> str:
        """Filter out unnecessary technical details from output.

        Args:
            output: Raw output string

        Returns:
            Output with technical details filtered
        """
        # Remove debug information
        output = re.sub(r'(?i)debug\s*:\s*[^\n]+\n', '', output)

        # Remove verbose technical paths
        output = re.sub(r'(?:/[\w\-.]+)+\.py:\d+', '', output)

        # Remove memory addresses
        output = re.sub(r'0x[0-9a-fA-F]+', '[memory-address]', output)

        return output

    @staticmethod
    def create_structured_output(content: str) -> str:
        """Create a structured output with clear separation between steps and final output.

        Args:
            content: The content to structure

        Returns:
            Structured output with clear sections
        """
        if not content:
            return ""

        # Check if there's already a final output section
        final_output_match = re.search(r'## Final Output\s*\n(.+?)(?=\n##|$)', content, re.DOTALL)

        if final_output_match:
            # Extract the final output section
            final_output = final_output_match.group(1).strip()

            # Remove the final output section from the original content
            implementation_steps = re.sub(r'\n## Final Output\s*\n(.+?)(?=\n##|$)', '', content, flags=re.DOTALL)

            # Format the implementation steps
            if not implementation_steps.startswith("## Implementation Steps"):
                implementation_steps = "## Implementation Steps\n\n" + implementation_steps
        else:
            # If no final output section exists, create one
            # Take the last paragraph as the final output
            paragraphs = content.split("\n\n")

            if len(paragraphs) > 1:
                final_output = paragraphs[-1]
                implementation_steps = "\n\n".join(paragraphs[:-1])

                # Format the implementation steps
                if not implementation_steps.startswith("## Implementation Steps"):
                    implementation_steps = "## Implementation Steps\n\n" + implementation_steps
            else:
                # If there's only one paragraph, use it as both implementation and final output
                final_output = content
                implementation_steps = "## Implementation Steps\n\nNo detailed steps required for this simple task."

        # Format the final output
        if not final_output.startswith("## Final Output"):
            final_output = "## Final Output\n\n" + final_output

        # Combine the sections with clear separation
        structured_output = f"{implementation_steps.strip()}\n\n---\n\n{final_output.strip()}"

        return structured_output

    @staticmethod
    def create_summary(output: str, max_length: int = 150) -> str:
        """Create a concise summary of the output.

        Args:
            output: Full output string
            max_length: Maximum length of summary

        Returns:
            Concise summary of the output
        """
        if not output:
            return ""

        # Check if there's a final output section
        final_output_match = re.search(r'## Final Output\s*\n(.+?)(?=\n##|$)', output, re.DOTALL)
        if final_output_match:
            # Use the final output section for the summary
            summary_text = final_output_match.group(1).strip()
        else:
            # Use the full output
            summary_text = output

        # Remove code blocks for summary
        no_code = re.sub(r'```[\s\S]*?```', '', summary_text)

        # Remove markdown formatting
        no_markdown = re.sub(r'[\*_~`#]', '', no_code)

        # Remove extra whitespace
        no_markdown = re.sub(r'\s+', ' ', no_markdown).strip()

        # Get first few sentences
        sentences = re.split(r'(?<=[.!?])\s+', no_markdown)
        summary = ""

        for sentence in sentences:
            if len(summary) + len(sentence) <= max_length:
                summary += sentence + " "
            else:
                # If we can't fit the whole sentence, add a truncated version with ellipsis
                if not summary:
                    remaining_length = max_length - 3  # Account for ellipsis
                    summary = sentence[:remaining_length] + "..."
                break

        return summary.strip()
