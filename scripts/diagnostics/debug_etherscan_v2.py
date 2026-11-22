import requests
from bs4 import BeautifulSoup

url = "https://etherscan.io/address/0xbe0eb53f46cd790cd13851d5eff43d12404d33e8" # Binance 7
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}

try:
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    with open("etherscan_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
        
    print("Saved response to etherscan_debug.html")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.title.text if soup.title else "No Title"
    print(f"Title: {title}")
    
    if "Just a moment" in title or "Cloudflare" in response.text:
        print("🚨 Cloudflare Detected!")
        
    label = soup.find('span', {'id': 'spanLabelName'})
    if label:
        print(f"✅ Label found: {label.text}")
    else:
        print("❌ Label NOT found")

except Exception as e:
    print(f"Error: {e}")

