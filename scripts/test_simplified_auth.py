#!/usr/bin/env python3
"""Test the simplified authentication approach from the working Aula client."""

import sys
import os
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
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
        return None, None
    
    return username, password

def test_simplified_auth():
    """Test the simplified authentication approach."""
    print("🔬 Testing Simplified Authentication (from working Aula client)")
    print("=" * 70)
    
    username, password = load_credentials()
    if not username:
        return False
    
    print(f"Testing with username: {username}")
    
    session = requests.Session()
    
    try:
        # Step 1: Get initial login page (simplified)
        print("\n📍 Step 1: Getting initial login page...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        params = {"type": "unilogin"}
        response = session.get(
            "https://login.aula.dk/auth/login.php",
            params=params,
            headers=headers,
            verify=True,
        )
        
        print(f"✅ Response status: {response.status_code}")
        
        html = BeautifulSoup(response.text, "lxml")
        url = html.form["action"]
        print(f"✅ Form action: {url}")
        
        # Step 2: Submit IdP selection (simplified)
        print("\n📍 Step 2: Submitting IdP selection...")
        headers = {
            "Host": "broker.unilogin.dk",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "null",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        data = {"selectedIdp": "uni_idp"}
        response = session.post(url, headers=headers, data=data, verify=True)
        
        print(f"✅ Response status: {response.status_code}")
        
        # Step 3: Complete authentication flow (simplified)
        print("\n📍 Step 3: Following authentication flow...")
        user_data = {
            "username": username,
            "password": password,
            "selected-aktoer": "KONTAKT",
        }
        
        redirects = 0
        success = False
        
        while not success and redirects < 10:
            print(f"🔄 Redirect {redirects}: {response.url}")
            
            html = BeautifulSoup(response.text, "lxml")
            url = html.form["action"]
            
            post_data = {}
            for input_elem in html.find_all("input"):
                if input_elem.has_attr("name") and input_elem.has_attr("value"):
                    post_data[input_elem["name"]] = input_elem["value"]
                    for key in user_data:
                        if input_elem.has_attr("name") and input_elem["name"] == key:
                            post_data[key] = user_data[key]
            
            response = session.post(url, data=post_data, verify=True)
            
            if response.url == "https://www.aula.dk:443/portal/":
                success = True
                print("🎉 Authentication successful!")
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
    test_simplified_auth()