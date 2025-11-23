#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

# Try multiple paths
current_dir = Path(__file__).resolve().parent
root_candidate_1 = current_dir.parents[2] # scripts/subprojects/risk_ai -> root
root_candidate_2 = current_dir.parents[3] # scripts/subprojects/risk_ai -> root (current code)

print(f"Current Dir: {current_dir}")
print(f"Candidate 1: {root_candidate_1}")
print(f"Candidate 2: {root_candidate_2}")

env_path_1 = root_candidate_1 / "config" / ".env"
env_path_2 = root_candidate_2 / "config" / ".env"

print(f"Env Path 1 Exists: {env_path_1.exists()}")
print(f"Env Path 2 Exists: {env_path_2.exists()}")

load_dotenv(env_path_1)
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')}")
print(f"SUPABASE_ANON_KEY: {os.getenv('SUPABASE_ANON_KEY')}")
print(f"SUPABASE_SERVICE_ROLE_KEY: {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}")

