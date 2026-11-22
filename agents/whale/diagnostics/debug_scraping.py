import requests
from bs4 import BeautifulSoup

# 알려진 바이낸스 지갑 (Binance 7)
url = "https://etherscan.io/address/0xbe0eb53f46cd790cd13851d5eff43d12404d33e8"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

try:
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for Cloudflare challenge
        if "cloudflare" in response.text.lower():
            print("⚠️ Cloudflare detected!")
        
        # Check for specific element
        label_span = soup.find('span', {'id': 'spanLabelName'})
        title = soup.title.text if soup.title else "No Title"
        
        print(f"Page Title: {title}")
        if label_span:
            print(f"Found Label: {label_span.text.strip()}")
        else:
            print("❌ 'spanLabelName' not found.")
            # Print a snippet of body to see what we got
            print(f"Body snippet: {response.text[:500]}...")
    else:
        print("Request failed.")

except Exception as e:
    print(f"Error: {e}")

