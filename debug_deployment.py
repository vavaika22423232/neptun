#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug script for deployment troubleshooting
"""

import sys
import os

print("🔧 Deployment Debug Information")
print("=" * 40)

print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"Current working directory: {os.getcwd()}")

# Check SpaCy installation
try:
    import spacy
    print(f"✅ SpaCy version: {spacy.__version__}")
    
    # Try to load the model
    try:
        nlp = spacy.load('uk_core_news_sm')
        print("✅ Ukrainian model uk_core_news_sm loaded successfully")
        
        # Test basic functionality
        doc = nlp("Удар по Києву")
        print(f"✅ Basic NLP test: {len(doc)} tokens, {len(doc.ents)} entities")
        for ent in doc.ents:
            print(f"   - {ent.text} ({ent.label_})")
            
    except OSError as e:
        print(f"❌ Ukrainian model not found: {e}")
        print("💡 Try: python -m spacy download uk_core_news_sm")
        
except ImportError as e:
    print(f"❌ SpaCy not installed: {e}")

# Check other dependencies
modules_to_check = ['flask', 'telethon', 'pytz', 'requests']
for module in modules_to_check:
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        print(f"✅ {module}: {version}")
    except ImportError:
        print(f"❌ {module}: not installed")

print("\n🎯 Ready for deployment test")
