import os
from dotenv import load_dotenv
from supabase import create_client

def confirm_admin_user():
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_KEY")
    
    if not url or not service_key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env file.")
        return

    # Use the service role key to get admin privileges
    supabase = create_client(url, service_key)
    
    try:
        # Search for the user by email to get their ID if we don't have it (though we do from before)
        # But it's safer to just search
        user_id = "b5cbc841-d37e-4575-bb58-5d03e8c04ea4" # From the previous output
        
        # Update user to be confirmed
        res = supabase.auth.admin.update_user_by_id(
            user_id,
            {"email_confirm": True}
        )
        print(f"Success! User {res.user.email} has been manually confirmed.")
        print("You should now be able to log in.")
    except Exception as e:
        print(f"Error confirming user: {e}")
        print("Note: This requires the SUPABASE_KEY to be the Service Role Key, not the Anon Key.")

if __name__ == "__main__":
    confirm_admin_user()
