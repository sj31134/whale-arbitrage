import os
import sys
import sqlite3
import pandas as pd
import time
from pathlib import Path
from datetime import datetime

# Add project root to path to allow importing from src
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.collectors.multi_chain_collector import (
    fetch_etherscan_transactions,
    fetch_sochain_transactions,
    ETHERSCAN_API_KEY,
    SOCHAIN_API_KEY
)

DB_PATH = ROOT / "data" / "project.db"

def get_whale_addresses(chain_type):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT address FROM whale_address WHERE chain_type = ?"
    df = pd.read_sql(query, conn, params=(chain_type,))
    conn.close()
    return df['address'].tolist()

def save_transactions(transactions):
    if not transactions:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for tx in transactions:
        try:
            cursor.execute("""
            INSERT OR IGNORE INTO whale_transactions 
            (tx_hash, chain, block_number, block_timestamp, from_address, to_address, value, coin_symbol, gas_used, gas_price, is_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx['tx_hash'],
                tx['chain'],
                tx['block_number'],
                tx['block_timestamp'],
                tx['from_address'],
                tx['to_address'],
                tx['value'],
                tx['coin_symbol'],
                tx.get('gas_used'),
                tx.get('gas_price'),
                tx['is_error']
            ))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"Error saving tx {tx.get('tx_hash')}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Saved {count} new transactions.")

def collect_eth_data():
    print("Collecting ETH whale transactions...")
    addresses = get_whale_addresses('ETH')
    print(f"Found {len(addresses)} ETH whale addresses.")
    
    # Process in batches to avoid overwhelming (though the collector function iterates one by one)
    # But passing all at once is fine as the function handles it.
    # However, to save progress incrementally, maybe we can batch.
    
    batch_size = 5
    for i in range(0, len(addresses), batch_size):
        batch = addresses[i:i+batch_size]
        print(f"Processing ETH batch {i+1}-{min(i+batch_size, len(addresses))}...")
        try:
            txs = fetch_etherscan_transactions(batch, 'ethereum', ETHERSCAN_API_KEY)
            save_transactions(txs)
        except Exception as e:
            print(f"Error in ETH batch {i}: {e}")
        
        time.sleep(1) # Extra pause between batches

def collect_btc_data():
    print("Collecting BTC whale transactions...")
    addresses = get_whale_addresses('BTC')
    print(f"Found {len(addresses)} BTC whale addresses.")
    
    batch_size = 5
    for i in range(0, len(addresses), batch_size):
        batch = addresses[i:i+batch_size]
        print(f"Processing BTC batch {i+1}-{min(i+batch_size, len(addresses))}...")
        try:
            txs = fetch_sochain_transactions(batch, 'BTC', SOCHAIN_API_KEY)
            save_transactions(txs)
        except Exception as e:
            print(f"Error in BTC batch {i}: {e}")
        
        time.sleep(1)

def main():
    if not ETHERSCAN_API_KEY:
        print("Warning: ETHERSCAN_API_KEY not found.")
    
    collect_eth_data()
    collect_btc_data()
    print("Collection complete.")

if __name__ == "__main__":
    main()

