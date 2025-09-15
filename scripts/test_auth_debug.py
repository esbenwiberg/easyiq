#!/usr/bin/env python3
"""Debug authentication issues with detailed logging."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'easyiq'))

import requests
from bs4 import BeautifulSoup
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    
    if not username or not password:
        print("❌ Credentials not found in .env file")
        print("Please create a .env file with EASYIQ_USERNAME and EASYIQ_PASSWORD")
        return None, None
    
    return username, password

def test_authentication_step_by_step():
    """Test authentication with detailed step-by-step logging."""
    print("🔬 Testing Authentication Step by Step")
    print("=" * 60)
    
    username, password = load_credentials()
    if not username:
        return False
    
    print(f"Testing with username: {username}")
    
    session = requests.Session()
    
    try:
        # Step 1: Get initial login page
        print("\n📍 Step 1: Getting initial login page...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
        }
        params = {"type": "unilogin"}
        response = session.get(
            "https://login.aula.dk/auth/login.php",
            params=params,
            headers=headers,
            verify=True,
            timeout=30,
        )
        
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response URL: {response.url}")
        print(f"✅ Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ Login page returned status {response.status_code}")
            return False
        
        # Parse the form
        html = BeautifulSoup(response.text, "html.parser")
        if not html.form:
            print("❌ No form found in login page response")
            print(f"Response text preview: {response.text[:500]}")
            return False
        
        form_action = html.form.get("action")
        print(f"✅ Form action: {form_action}")
        
        # Step 2: Submit IdP selection
        print("\n📍 Step 2: Submitting IdP selection...")
        data = {"selectedIdp": "uni_idp"}
        response = session.post(form_action, data=data, verify=True, timeout=30)
        
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response URL: {response.url}")
        
        # Step 3: Follow authentication flow
        print("\n📍 Step 3: Following authentication flow...")
        user_data = {
            "username": username,
            "password": password,
            "selected-aktoer": "KONTAKT",
        }
        
        redirects = 0
        success = False
        
        while not success and redirects < 10:
            print(f"\n🔄 Redirect {redirects}:")
            print(f"   Current URL: {response.url}")
            print(f"   Status: {response.status_code}")
            
            html = BeautifulSoup(response.text, "html.parser")
            if not html.form:
                print(f"❌ No form found in authentication step {redirects}")
                print(f"Response text preview: {response.text[:500]}")
                break
            
            url = html.form.get("action")
            print(f"   Form action: {url}")
            
            # Build post data
            post_data = {}
            for input_elem in html.find_all("input"):
                if input_elem.has_attr("name") and input_elem.has_attr("value"):
                    post_data[input_elem["name"]] = input_elem["value"]
                    # Override with user data if applicable
                    for key in user_data:
                        if input_elem.has_attr("name") and input_elem["name"] == key:
                            post_data[key] = user_data[key]
            
            print(f"   Post data keys: {list(post_data.keys())}")
            
            response = session.post(url, data=post_data, verify=True, timeout=30)
            
            print(f"   After POST - URL: {response.url}")
            print(f"   After POST - Status: {response.status_code}")
            
            # Check for success
            if response.url in ["https://www.aula.dk:443/portal/", "https://www.aula.dk/portal/"]:
                success = True
                print("🎉 Authentication successful - reached Aula portal!")
                break
            
            redirects += 1
        
        if not success:
            print(f"❌ Authentication failed after {redirects} redirects")
            print(f"Final URL: {response.url}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_authentication_step_by_step()