#!/usr/bin/env python3
"""
Debug script to see what's actually on the Aula login page.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def debug_login_page():
    """Debug the login page content."""
    print("🔍 Debugging Aula login page content")
    print("=" * 50)
    
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
    
    # Create a fresh session with no cookies
    connector = aiohttp.TCPConnector(ssl=True)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        cookie_jar=aiohttp.CookieJar()
    ) as session:
        
        # Test multiple URLs
        urls_to_test = [
            "https://login.aula.dk/",
            "https://login.aula.dk/auth/login.php?type=unilogin",
            "https://www.aula.dk/",
        ]
        
        for url in urls_to_test:
            print(f"\n🌐 Testing URL: {url}")
            print("-" * 60)
            
            try:
                async with session.get(url, headers=headers, allow_redirects=False) as response:
                    print(f"Status: {response.status}")
                    print(f"Final URL: {response.url}")
                    print(f"Headers: {dict(response.headers)}")
                    
                    if response.status in [301, 302, 303, 307, 308]:
                        location = response.headers.get("Location", "No location header")
                        print(f"Redirect to: {location}")
                        continue
                    
                    content = await response.text()
                    print(f"Content length: {len(content)}")
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")
                    
                    # Look for login-related elements
                    print("\n📋 Login-related elements:")
                    
                    # Check for Unilogin text
                    unilogin_elements = soup.find_all(string=lambda text: text and "unilogin" in text.lower())
                    if unilogin_elements:
                        print("  Found Unilogin text elements:")
                        for elem in unilogin_elements:
                            parent = elem.parent
                            print(f"    - '{elem.strip()}' in {parent.name if parent else 'unknown'}")
                            if parent and parent.name == "a":
                                print(f"      Link href: {parent.get('href', 'No href')}")
                    
                    # Check for login buttons/links
                    login_elements = soup.find_all(string=lambda text: text and "login" in text.lower())
                    if login_elements:
                        print("  Found login text elements:")
                        for elem in login_elements[:5]:  # Limit to first 5
                            parent = elem.parent
                            print(f"    - '{elem.strip()}' in {parent.name if parent else 'unknown'}")
                    
                    # Check for forms
                    forms = soup.find_all("form")
                    if forms:
                        print("  Found forms:")
                        for i, form in enumerate(forms):
                            print(f"    Form {i+1}: action='{form.get('action', 'No action')}'")
                            inputs = form.find_all("input")
                            for inp in inputs[:3]:  # Limit to first 3 inputs
                                print(f"      Input: {inp.get('name', 'No name')} = {inp.get('value', 'No value')}")
                    
                    # Check for clickable elements
                    clickable = soup.find_all(["a", "button"], href=True) + soup.find_all(["div", "span"], onclick=True)
                    if clickable:
                        print("  Found clickable elements:")
                        for elem in clickable[:5]:  # Limit to first 5
                            text = elem.get_text(strip=True)[:50]  # Limit text length
                            if elem.name == "a":
                                print(f"    Link: '{text}' -> {elem.get('href', 'No href')}")
                            else:
                                print(f"    {elem.name}: '{text}' onclick='{elem.get('onclick', 'No onclick')}'")
                    
                    print(f"\n📄 Content preview (first 1000 chars):")
                    print(content[:1000])
                    
            except Exception as e:
                print(f"Error accessing {url}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_login_page())