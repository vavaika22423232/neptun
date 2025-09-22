#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test application startup without SpaCy
"""

import os
import sys

# Simulate SpaCy not being available
sys.modules['spacy'] = None

# Now try to import our app
try:
    from app import app, SPACY_AVAILABLE
    print(f"✅ App imported successfully")
    print(f"📊 SPACY_AVAILABLE: {SPACY_AVAILABLE}")
    
    if not SPACY_AVAILABLE:
        print("✅ System works without SpaCy - fallback mechanism active")
    else:
        print("⚠️ SpaCy was loaded despite being disabled")
        
except Exception as e:
    print(f"❌ App import failed: {e}")
    sys.exit(1)

print("🎉 Deploy compatibility test passed!")
