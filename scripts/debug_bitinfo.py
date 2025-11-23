import requests
from bs4 import BeautifulSoup

url = "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find table rows
        rows = soup.find_all('tr')
        print(f"Found {len(rows)} rows.")
        
        # Print first few rows to check structure
        for i, row in enumerate(rows[:10]):
            print(f"Row {i}: {row.text[:100]}...")
            
            # Try to find address link
            links = row.find_all('a')
            for link in links:
                href = link.get('href')
                if href and 'bitcoin/address/' in href:
                    print(f"  Address Link: {href}")
                    # Check for label? usually in small tag or next to it
                    print(f"  Text: {link.text}")
                    
                    # Check for wallet label
                    # BitInfoCharts often puts label in a <small> tag or directly in td
                    # Example: 1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ (Huobi-coldwallet)
                    # Let's inspect the parent td
                    td = link.find_parent('td')
                    if td:
                        print(f"  Full TD text: {td.text.strip()}")

    else:
        print("Request failed.")

except Exception as e:
    print(f"Error: {e}")

