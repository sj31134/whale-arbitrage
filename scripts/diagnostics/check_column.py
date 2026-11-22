#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

load_dotenv(Path.cwd() / 'config' / '.env')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("Checking column...")
try:
    supabase.table('whale_transactions').select('transaction_direction').limit(1).execute()
    print("✅ Column exists!")
except Exception as e:
    print(f"❌ Column missing or error: {e}")

