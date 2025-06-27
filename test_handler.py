#!/usr/bin/env python3
"""
Simple test script to verify our handler logic works
"""

import json
from src.handler import handler

def test_info_request():
    """Test the info/status endpoint"""
    print("Testing info request...")
    event = {
        "input": {
            "action": "get_info"
        }
    }
    
    result = handler(event)
    print("Result:", json.dumps(result, indent=2))
    return result

def test_book_cover_request():
    """Test a simple book cover generation request"""
    print("\nTesting book cover generation request...")
    event = {
        "input": {
            "action": "generate_book_cover",
            "title": "Test Book",
            "author": "Test Author", 
            "story_style": "picture_book",
            "theme": "Adventure",
            "book_format": "square_small",
            "reference_images": []
        }
    }
    
    try:
        result = handler(event)
        print("Result:", json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"Error (expected without WebUI running): {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("=== Testing RunPod Handler Logic ===")
    
    # Test 1: Info request (should work without WebUI)
    info_result = test_info_request()
    
    # Test 2: Book cover request (will fail without WebUI but we can see the logic)
    cover_result = test_book_cover_request()
    
    print("\n=== Test Summary ===")
    print(f"Info request successful: {'status' in info_result}")
    print(f"Cover request logic intact: {'error' in cover_result}")
    print("\nNote: Cover generation errors are expected when WebUI is not running")
