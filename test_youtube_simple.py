#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test for YouTube metadata JSON parsing
"""

import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Test string that seems to be causing the error
test_response = '''
  "titles": {
    "chinese": ["标题1", "标题2", "标题3"],
    "english": ["Title 1", "Title 2", "Title 3"]
  }
}'''

# This is what the error message showed
error_string = '\n  "titles"'

print("Testing JSON parsing...")
print(f"Error string repr: {repr(error_string)}")

# Try to parse the test response
try:
    result = json.loads(test_response)
    print("Success!")
except json.JSONDecodeError as e:
    print(f"Failed: {e}")
    print(f"Error at position: {e.pos}")
    print(f"String around error: {repr(test_response[max(0, e.pos-20):min(len(test_response), e.pos+20)])}")

# Test with missing opening brace
incomplete_json = '''
  "titles": {
    "chinese": ["标题1", "标题2", "标题3"],
    "english": ["Title 1", "Title 2", "Title 3"]
  }
}'''

print("\nTesting incomplete JSON (missing opening brace)...")
try:
    result = json.loads(incomplete_json)
    print("Success!")
except json.JSONDecodeError as e:
    print(f"Failed as expected: {e}")
    # Extract the error string
    error_preview = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"Error preview: {repr(error_preview)}")