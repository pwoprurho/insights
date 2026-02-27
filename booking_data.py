from db import get_supabase
import logging

def save_booking(name, email, phone_number, service, date):
    try:
        supabase = get_supabase()
        data = {
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "service": service,
            "date": date
        }
        res = supabase.table("bookings").insert(data).execute()
        return res.data
    except Exception as e:
        logging.error(f"Error saving booking to Supabase: {e}")
        return None

def load_bookings():
    try:
        supabase = get_supabase()
        # Fetching all bookings, ordered by creation date descending
        res = supabase.table("bookings").select("*").order("created_at", desc=True).execute()
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Error loading bookings from Supabase: {e}")
        return []
