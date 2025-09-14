#!/usr/bin/env python3

from app import process_message
import json
from datetime import datetime

# Test the original problematic message
test_message = "Харківщина — БпЛА на Гути"

print(f"Testing message: '{test_message}'")
print()

# Call with required parameters
result = process_message(test_message, "test_mid_001", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "test_channel")
print("Processing result:")
print(json.dumps(result, indent=2, ensure_ascii=False))
