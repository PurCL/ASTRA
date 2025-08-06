#!/usr/bin/env python3
"""
Test script for the new query_model function.
"""

import sys
import os

# Add the parent directory to the path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporal_explorator.utils.chat_utils import query_model, chat_with_model, extract_tag

def test_extract_tag():
    """Test the extract_tag function."""
    print("Testing extract_tag function...")
    
    # Test with XML tags
    text1 = "Here is some text <State>JAILBROKEN</State> and more text"
    result1 = extract_tag(text1, "State")
    print(f"Test 1 - XML tags: {result1}")  # Expected: "JAILBROKEN"
    
    # Test with markdown pattern
    text2 = "Here is some text ### State JAILBROKEN ### Reasoning This is reasoning"
    result2 = extract_tag(text2, "State")
    print(f"Test 2 - Markdown pattern: {result2}")  # Expected: "JAILBROKEN"
    
    # Test with missing tag
    text3 = "Here is some text without any tags"
    result3 = extract_tag(text3, "State")
    print(f"Test 3 - Missing tag: {result3}")  # Expected: None

def test_query_model_simulation():
    """Simulate query_model function behavior."""
    print("\nTesting query_model function simulation...")
    
    # Simulate a response with multiple tags
    mock_response = """
    Here is some analysis:
    
    <State>JAILBROKEN</State>
    <Reasoning>This response contains harmful content that could be used maliciously.</Reasoning>
    <Confidence>0.95</Confidence>
    """
    
    # Test extracting multiple tags
    tag_names = ["State", "Reasoning", "Confidence"]
    extracted_tags = {}
    
    for tag_name in tag_names:
        extracted_content = extract_tag(mock_response, tag_name)
        if extracted_content is not None:
            extracted_tags[tag_name] = extracted_content
    
    print(f"Extracted tags: {extracted_tags}")
    
    # Test extracting non-existent tag
    non_existent_result = extract_tag(mock_response, "NonExistent")
    print(f"Non-existent tag result: {non_existent_result}")

def test_backward_compatibility():
    """Test backward compatibility with chat_with_model."""
    print("\nTesting backward compatibility...")
    
    # This would normally call the actual model, but we'll just test the function signature
    print("chat_with_model function is available for backward compatibility")
    print("query_model function is the new recommended function")

if __name__ == "__main__":
    print("Testing query_model and related functions...")
    test_extract_tag()
    test_query_model_simulation()
    test_backward_compatibility()
    print("\nAll tests completed!") 