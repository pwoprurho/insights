import os
from supabase_client import supabase

def create_bucket():
    bucket_name = 'blog-assets'
    try:
        # Check if bucket already exists
        buckets = supabase.storage.list_buckets()
        bucket_exists = any(b.name == bucket_name for b in buckets)
        
        if bucket_exists:
            print(f"Bucket '{bucket_name}' already exists.")
            return

        print(f"Creating bucket '{bucket_name}'...")
        # Create a new public bucket
        res = supabase.storage.create_bucket(bucket_name, name=bucket_name, options={"public": True})
        print(f"Successfully created bucket: {res}")
        
    except Exception as e:
        print(f"Error creating bucket: {e}")

if __name__ == "__main__":
    create_bucket()
