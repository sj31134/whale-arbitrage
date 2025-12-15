import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "project.db"
CSV_PATH = ROOT / "data" / "richlist" / "whale_address_cleaned.csv"

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create whale_address table
    print("Creating whale_address table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whale_address (
        id VARCHAR(50) PRIMARY KEY,
        chain_type VARCHAR(20),
        address VARCHAR(100),
        name_tag VARCHAR(100),
        balance VARCHAR(50),
        percentage VARCHAR(20),
        txn_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_address_chain ON whale_address(chain_type);")

    # 2. Import CSV data
    if CSV_PATH.exists():
        print(f"Importing data from {CSV_PATH}...")
        df = pd.read_csv(CSV_PATH)
        # Rename columns to match table schema if necessary, or just rely on order/names
        # CSV columns: id,chain_type,address,name_tag,balance,percentage,txn_count
        
        # Check for existing IDs to avoid duplicates if re-running
        existing_ids = pd.read_sql("SELECT id FROM whale_address", conn)['id'].tolist()
        df_new = df[~df['id'].isin(existing_ids)]
        
        if not df_new.empty:
            df_new.to_sql('whale_address', conn, if_exists='append', index=False)
            print(f"Imported {len(df_new)} rows.")
        else:
            print("No new rows to import.")
    else:
        print(f"Warning: CSV file not found at {CSV_PATH}")

    # 3. Create whale_transactions table
    print("Creating whale_transactions table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whale_transactions (
        tx_hash VARCHAR(100),
        chain VARCHAR(20),
        block_number INTEGER,
        block_timestamp TIMESTAMP,
        from_address VARCHAR(100),
        to_address VARCHAR(100),
        value DECIMAL(30, 18),
        coin_symbol VARCHAR(20),
        gas_used INTEGER,
        gas_price INTEGER,
        is_error BOOLEAN,
        from_label VARCHAR(255),
        to_label VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (tx_hash, chain)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_tx_timestamp ON whale_transactions(block_timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_tx_from ON whale_transactions(from_address);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_tx_to ON whale_transactions(to_address);")

    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()

