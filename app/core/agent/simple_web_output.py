"""
Simplified WebOutputFormatter implementation to avoid import issues.
"""

class WebOutputFormatter:
    """Formatter for web output."""
    
    def format_output(self, output: str) -> str:
        """Format output for web display."""
        return output
    
    def structure_tool_result(self, result: str) -> str:
        """Structure tool result for web display."""
        return result
    
    def create_summary(self, output: str, max_length: int = 150) -> str:
        """Create a summary of the output."""
        if not output:
            return ""
        
        if len(output) <= max_length:
            return output
        
        return output[:max_length] + "..."
