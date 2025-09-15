#!/usr/bin/env python3
"""
Test the original Aula client to see if authentication works.
"""

import os
import sys

def load_credentials():
    """Load credentials from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD')
    
    if not password:
        print("❌ EASYIQ_PASSWORD not found in environment")
        sys.exit(1)
    
    return username, password

def main():
    print("🔬 Testing Original Aula Client")
    print("=" * 40)
    
    # Import original Aula client
    sys.path.append('aula/custom_components/aula')
    from client import Client
    
    username, password = load_credentials()
    
    print(f"Testing with username: {username}")
    
    # Create client
    client = Client(username, password, False, False, False)
    
    # Test login
    try:
        result = client.login()
        print(f"Login result: {result}")
        
        if result:
            print("✅ Original Aula client authentication successful!")
        else:
            print("❌ Original Aula client authentication failed")
            
    except Exception as e:
        print(f"❌ Exception during login: {e}")

if __name__ == "__main__":
    main()