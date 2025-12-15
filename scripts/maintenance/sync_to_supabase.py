import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Project Setup
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / "config" / ".env")

DB_PATH = ROOT / "data" / "project.db"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found.")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_table(table_name, batch_size=1000):
    supabase = get_supabase_client()
    if not supabase:
        return

    print(f"Syncing table {table_name}...")
    conn = sqlite3.connect(DB_PATH)
    
    # Read total count
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cursor.fetchone()[0]
    print(f"Total rows in SQLite {table_name}: {total_rows}")

    # Read and upsert in batches
    for offset in range(0, total_rows, batch_size):
        query = f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
        df = pd.read_sql(query, conn)
        
        # Convert DataFrame to records
        # Handle date conversion if necessary (Supabase expects ISO strings)
        if 'created_at' in df.columns:
            df['created_at'] = df['created_at'].astype(str)
        if 'block_timestamp' in df.columns:
            df['block_timestamp'] = df['block_timestamp'].astype(str)
            
        records = df.to_dict(orient='records')
        
        try:
            # Upsert to Supabase
            response = supabase.table(table_name).upsert(records).execute()
            print(f"Synced batch {offset}-{offset+len(records)}")
        except Exception as e:
            print(f"Error syncing batch {offset}: {e}")
            # Optional: break or continue?
            
    conn.close()
    print(f"Sync complete for {table_name}.")

def main():
    sync_table("whale_address")
    sync_table("whale_transactions")

if __name__ == "__main__":
    main()

