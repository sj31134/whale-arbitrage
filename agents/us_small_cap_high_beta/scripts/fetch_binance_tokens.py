import requests
import json

symbols_to_fetch = [
    ("RKLBUSDT", "Rocket Lab USA", "Space Systems / Launch Infrastructure ($10 Multi-Bagger Breakout)"),
    ("ASTSUSDT", "AST SpaceMobile", "Direct-to-Cell Satellite Broadband (Telecommunications Monopoly)"),
    ("IRENUSDT", "IREN (Iris Energy)", "Renewable Power to AI Cloud HPC Data Centers (Sub-$10 Supercycle)"),
    ("PLTRUSDT", "Palantir Technologies", "Defense & Enterprise AI Ontology OS (Government Moat)"),
    ("ARMUSDT", "Arm Holdings", "Semiconductor Architecture IP Monopoly (Royalty Power)"),
    ("ASMLUSDT", "ASML Holding", "High-NA EUV Lithography 100% Global Monopoly (Foundry Bottleneck)"),
    ("TSMUSDT", "TSMC", "Advanced 3nm/2nm AI Foundry (92% Global Share)"),
    ("NVDAUSDT", "NVIDIA Corporation", "Blackwell AI Compute & CUDA Hardware Infrastructure"),
    ("TSLAUSDT", "Tesla Inc.", "Autonomous FSD & Megapack Energy Storage Physical AI"),
    ("COINUSDT", "Coinbase Global", "US Institutional Crypto Custody & Exchange Infrastructure"),
    ("MSTRUSDT", "MicroStrategy", "Bitcoin Treasury Reserve Corporate Vehicle"),
    ("PAXGUSDT", "PAX Gold", "LBMA 1oz Physical Gold Tokenized RWA"),
    ("ONDOUSDT", "Ondo Finance", "Tokenized US Treasuries (OUSG/USDY) RWA Infrastructure Protocol")
]

print("=" * 100)
print(f"📡 QUERYING REAL BINANCE 24/7 API FOR {len(symbols_to_fetch)} GENUINE TOKENIZED STOCKS / RWAs")
print("=" * 100)

results = []
for sym, name, thesis in symbols_to_fetch:
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={sym}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            price = float(d["lastPrice"])
            price_change_pct = float(d["priceChangePercent"])
            volume_24h = float(d["volume"])
            quote_vol_24h = float(d["quoteVolume"])
            high_24h = float(d["highPrice"])
            low_24h = float(d["lowPrice"])
            results.append({
                "symbol": sym,
                "name": name,
                "thesis": thesis,
                "price": price,
                "change_24h_pct": price_change_pct,
                "volume_24h": volume_24h,
                "quote_volume_usd": quote_vol_24h,
                "high_24h": high_24h,
                "low_24h": low_24h
            })
            print(f"✅ {sym:12s} | {name:25s} | Price: ${price:10.2f} | 24h Chg: {price_change_pct:+6.2f}% | 24h Vol: ${quote_vol_24h:14,.0f}")
        else:
            # Try spot
            spot_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}"
            r_spot = requests.get(spot_url, timeout=5)
            if r_spot.status_code == 200:
                d = r_spot.json()
                price = float(d["lastPrice"])
                price_change_pct = float(d["priceChangePercent"])
                quote_vol_24h = float(d["quoteVolume"])
                results.append({
                    "symbol": sym,
                    "name": name,
                    "thesis": thesis,
                    "price": price,
                    "change_24h_pct": price_change_pct,
                    "quote_volume_usd": quote_vol_24h,
                })
                print(f"✅ (Spot) {sym:12s} | {name:25s} | Price: ${price:10.2f} | 24h Chg: {price_change_pct:+6.2f}% | 24h Vol: ${quote_vol_24h:14,.0f}")
            else:
                print(f"❌ Failed to fetch {sym}: {r.status_code}")
    except Exception as e:
        print(f"❌ Error fetching {sym}: {e}")

print("\n" + "=" * 100)
print(f"Total verified real live Binance tokenized stock assets: {len(results)}")
print("=" * 100)
