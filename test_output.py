from app.agent.web_output import WebOutputFormatter

# Test with a simple output
test_output = "This is a test output with multiple paragraphs.\n\nHere is another paragraph.\n\nAnd a final paragraph that should be the final output."
structured_output = WebOutputFormatter.create_structured_output(test_output)
print("=== Test 1: Simple Output ===")
print(structured_output)
print("\n\n")

# Test with output that already has a Final Output section
test_output_with_final = "This is some implementation details.\n\n## Final Output\n\nThis is the final output section."
structured_output_with_final = WebOutputFormatter.create_structured_output(test_output_with_final)
print("=== Test 2: Output with Final Output Section ===")
print(structured_output_with_final)
print("\n\n")

# Test with a single paragraph
test_output_single = "This is a single paragraph output."
structured_output_single = WebOutputFormatter.create_structured_output(test_output_single)
print("=== Test 3: Single Paragraph Output ===")
print(structured_output_single)
