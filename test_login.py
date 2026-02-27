import os
from dotenv import load_dotenv
from supabase import create_client

def test_login():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    try:
        res = supabase.auth.sign_in_with_password({
            "email": "akporurho@proton.me",
            "password": "@mure3nny"
        })
        print("Login Success!")
        print(res.user)
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    test_login()
