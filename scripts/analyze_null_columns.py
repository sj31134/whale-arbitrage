#!/usr/bin/env python3
"""
Analyze NULL ratios and column significance for whale_transactions and price_history
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def analyze_nulls(supabase, table_name, limit=10000):
    print(f"\n📊 Analyzing {table_name} (Sample size: {limit})...")
    
    # Fetch sample data
    try:
        response = supabase.table(table_name).select('*').limit(limit).execute()
        data = response.data
        
        if not data:
            print("⚠️ No data found.")
            return
            
        df = pd.DataFrame(data)
        total_rows = len(df)
        
        analysis = []
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_ratio = (null_count / total_rows) * 100
            
            # Check for empty strings acting as nulls if it's object type
            if df[col].dtype == 'object':
                empty_count = (df[col] == '').sum()
                if empty_count > 0:
                    null_count += empty_count
                    null_ratio = (null_count / total_rows) * 100
            
            analysis.append({
                'Column': col,
                'Null Ratio (%)': round(null_ratio, 1),
                'Example Value': df[col].dropna().iloc[0] if not df[col].dropna().empty else 'ALL NULL'
            })
            
        # Sort by Null Ratio descending
        analysis_df = pd.DataFrame(analysis).sort_values('Null Ratio (%)', ascending=False)
        
        print(analysis_df.to_string(index=False))
        return analysis_df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    supabase = get_supabase_client()
    
    analyze_nulls(supabase, 'whale_transactions')
    analyze_nulls(supabase, 'price_history')

if __name__ == "__main__":
    main()

