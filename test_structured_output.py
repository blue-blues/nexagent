"""
Test script for the structured output formatting.

This script tests the WebOutputFormatter's create_structured_output method
with various types of input to ensure it correctly formats the output.
"""

from app.agent.web_output import WebOutputFormatter

def test_structured_output():
    """Test the structured output formatting with various inputs."""
    
    # Test cases
    test_cases = [
        {
            "name": "Simple output",
            "input": "This is a simple output.",
            "expected_sections": ["Implementation Steps", "Final Output"]
        },
        {
            "name": "Multi-paragraph output",
            "input": "This is the first paragraph.\n\nThis is the second paragraph.\n\nThis is the final paragraph.",
            "expected_sections": ["Implementation Steps", "Final Output"]
        },
        {
            "name": "Output with existing Final Output section",
            "input": "These are some implementation details.\n\n## Final Output\n\nThis is the final output.",
            "expected_sections": ["Implementation Steps", "Final Output"]
        },
        {
            "name": "Output with code blocks",
            "input": "Here's some code:\n\n```python\ndef hello():\n    print('Hello, world!')\n```\n\nAnd here's the result.",
            "expected_sections": ["Implementation Steps", "Final Output"]
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases):
        print(f"\n=== Test {i+1}: {test_case['name']} ===")
        
        # Format the output
        formatted = WebOutputFormatter.create_structured_output(test_case["input"])
        
        # Check if all expected sections are present
        all_sections_present = all(section in formatted for section in test_case["expected_sections"])
        
        # Print results
        print(f"Input: {test_case['input'][:50]}...")
        print(f"Formatted output:\n{formatted}")
        print(f"All expected sections present: {all_sections_present}")
        
        # Check for clear separation
        if "---" in formatted:
            print("Clear separation between sections: Yes")
        else:
            print("Clear separation between sections: No")

if __name__ == "__main__":
    test_structured_output()
