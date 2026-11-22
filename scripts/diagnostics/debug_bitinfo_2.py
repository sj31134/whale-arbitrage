import requests
from bs4 import BeautifulSoup

url = "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        
        for i, row in enumerate(rows[12:20]):  # Skip summary rows
            print(f"\nRow {i+12}:")
            text = row.text.strip()
            print(f"Text: {text[:100]}...")
            
            links = row.find_all('a')
            for link in links:
                href = link.get('href')
                if href and 'bitcoin/address/' in href:
                    addr = href.split('/')[-1]
                    print(f"  Addr: {addr}")
                    
                    # Look for label in small tag
                    small = link.find_next('small')
                    if small:
                        print(f"  Label (small): {small.text}")
                    
                    # Check if there is text after link in the same td
                    parent = link.parent
                    if parent:
                         print(f"  Parent text: {parent.text.strip()}")

    else:
        print("Request failed.")
except Exception as e:
    print(f"Error: {e}")

