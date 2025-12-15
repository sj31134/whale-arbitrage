import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "project.db"
EXPORT_DIR = ROOT / "data"

def export_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    print(f"Exporting {table_name} to CSV...")
    
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        # Sort by appropriate column if possible
        if 'date' in df.columns:
            df = df.sort_values('date')
        elif 'block_timestamp' in df.columns:
            df = df.sort_values('block_timestamp')
            
        csv_path = EXPORT_DIR / f"{table_name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Exported {len(df)} rows to {csv_path}")
    except Exception as e:
        print(f"Error exporting {table_name}: {e}")
    finally:
        conn.close()

def main():
    # Export the new whale tables
    export_table("whale_address")
    export_table("whale_transactions")
    
    # Also export other key tables just in case they were updated and not synced
    # (The user asked for "SQLite DB data to be pushed without omission")
    tables_to_export = [
        "upbit_daily", "binance_spot_daily", "bitget_spot_daily", "bybit_spot_daily",
        "exchange_rate", "binance_futures_metrics", "futures_extended_metrics",
        "binance_spot_weekly", "binance_futures_weekly", "bitinfocharts_whale",
        "bitinfocharts_whale_weekly", "whale_daily_stats", "whale_weekly_stats"
    ]
    
    for table in tables_to_export:
        export_table(table)

if __name__ == "__main__":
    main()

