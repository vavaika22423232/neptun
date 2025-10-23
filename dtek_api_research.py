"""
Research script to find DTEK API endpoints
This script analyzes DTEK website to discover how they fetch blackout data
"""

import requests
from bs4 import BeautifulSoup
import json
import re

# DTEK regional sites
DTEK_SITES = {
    'kyiv': 'https://www.dtek-krem.com.ua',
    'dnipro': 'https://www.dtek-dnem.com.ua',
    'odesa': 'https://www.dtek-oem.com.ua',
    'donetsk': 'https://www.dtek-donec.com.ua'
}

def extract_api_endpoints(html_content):
    """Extract potential API endpoints from HTML/JS"""
    
    # Look for common patterns
    api_patterns = [
        r'https?://[a-zA-Z0-9.-]+/api/[^\s"\'>]+',
        r'/api/v\d+/[^\s"\'>]+',
        r'fetch\([\'"]([^\'"]+)[\'"]',
        r'axios\.(get|post)\([\'"]([^\'"]+)[\'"]',
        r'\.ajax\(\{[^}]*url:\s*[\'"]([^\'"]+)[\'"]',
    ]
    
    endpoints = []
    for pattern in api_patterns:
        matches = re.findall(pattern, html_content)
        endpoints.extend(matches)
    
    return list(set(endpoints))

def analyze_dtek_site(region_name, base_url):
    """Analyze a DTEK site to find API endpoints"""
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {region_name} - {base_url}")
    print(f"{'='*60}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': base_url
    })
    
    try:
        # Fetch main page
        response = session.get(f"{base_url}/ua/shutdowns", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to fetch page")
            return
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for inline scripts
        scripts = soup.find_all('script')
        print(f"\nFound {len(scripts)} script tags")
        
        all_endpoints = []
        
        for i, script in enumerate(scripts):
            if script.string:
                endpoints = extract_api_endpoints(script.string)
                if endpoints:
                    print(f"\nScript #{i+1} endpoints:")
                    for ep in endpoints:
                        print(f"  - {ep}")
                        all_endpoints.append(ep)
        
        # Look for data attributes
        print("\n--- Data attributes ---")
        elements_with_data = soup.find_all(attrs={'data-api': True})
        for el in elements_with_data:
            print(f"Found data-api: {el.get('data-api')}")
        
        # Look for form actions
        print("\n--- Forms ---")
        forms = soup.find_all('form')
        for form in forms:
            action = form.get('action')
            if action:
                print(f"Form action: {action}")
        
        # Look for any JSON data in page
        print("\n--- JSON data ---")
        json_pattern = r'\{[^{}]*"api"[^{}]*\}'
        json_matches = re.findall(json_pattern, response.text)
        for match in json_matches[:5]:  # First 5 matches
            try:
                data = json.loads(match)
                print(f"JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                pass
        
        # Try common API endpoints
        print("\n--- Testing common endpoints ---")
        common_endpoints = [
            '/api/blackouts',
            '/api/shutdowns',
            '/api/v1/shutdowns',
            '/api/v1/address/search',
            '/api/address',
            '/api/outages',
            '/api/schedule',
            '/ua/shutdowns/search',
            '/ajax/shutdowns',
        ]
        
        for endpoint in common_endpoints:
            try:
                test_url = f"{base_url}{endpoint}"
                r = session.get(test_url, timeout=5)
                if r.status_code == 200:
                    print(f"✓ {endpoint} - Status: {r.status_code}")
                    try:
                        data = r.json()
                        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}")
                    except:
                        print(f"  Response (text): {r.text[:200]}")
            except Exception as e:
                pass
        
        # Check for GraphQL
        print("\n--- Testing GraphQL ---")
        graphql_endpoints = ['/graphql', '/api/graphql']
        for endpoint in graphql_endpoints:
            try:
                test_url = f"{base_url}{endpoint}"
                r = session.post(test_url, json={'query': '{__schema{types{name}}}'}, timeout=5)
                if r.status_code in [200, 400]:
                    print(f"✓ GraphQL at {endpoint}")
                    print(f"  Response: {r.text[:200]}")
            except:
                pass
                
    except Exception as e:
        print(f"Error: {e}")

def check_yasno_api():
    """Check YASNO API (they have better documented API)"""
    print(f"\n{'='*60}")
    print(f"Checking YASNO API")
    print(f"{'='*60}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })
    
    # Known YASNO endpoints
    yasno_endpoints = [
        'https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity',
        'https://api.yasno.com.ua/api/v1/address-search',
    ]
    
    for url in yasno_endpoints:
        try:
            print(f"\nTrying: {url}")
            r = session.get(url, timeout=10)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                except:
                    print(f"Response (text): {r.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    print("DTEK API Research Tool")
    print("="*60)
    
    # Analyze each DTEK regional site
    for region, url in DTEK_SITES.items():
        analyze_dtek_site(region, url)
    
    # Check YASNO
    check_yasno_api()
    
    print("\n" + "="*60)
    print("Research complete!")
    print("="*60)
