#!/usr/bin/env python3
"""Debug script to check import issues."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aula_easyiq'))

print("Testing imports directly...")

try:
    import requests
    print(f"✅ requests imported successfully: {requests}")
except ImportError as e:
    print(f"❌ requests import failed: {e}")

try:
    from bs4 import BeautifulSoup
    print(f"✅ BeautifulSoup imported successfully: {BeautifulSoup}")
except ImportError as e:
    print(f"❌ BeautifulSoup import failed: {e}")

print("\nNow testing client import...")

try:
    from client import EasyIQClient
    print("✅ Client imported successfully")
    
    # Check the imported values
    import client
    print(f"requests in client: {getattr(client, 'requests', 'NOT FOUND')}")
    print(f"BS4 in client: {getattr(client, 'BS4', 'NOT FOUND')}")
    
except ImportError as e:
    print(f"❌ Client import failed: {e}")
    import traceback
    traceback.print_exc()