import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            missing = []
            if not url: missing.append("SUPABASE_URL")
            if not key: missing.append("SUPABASE_KEY")
            raise ValueError(f"CRITICAL: Missing environment variables: {', '.join(missing)}. Please set them in your Railway dashboard.")
            
        _supabase = create_client(url, key)
    return _supabase

# Backward compatibility for direct import (might fail if accessed at top level)
class SupabaseProxy:
    def __getattr__(self, name):
        return getattr(get_supabase(), name)

supabase = SupabaseProxy()
