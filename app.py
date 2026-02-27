import os
import uuid
import sys
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

# Ensure logs are visible immediately
def log(msg):
    print(f"DEBUG: {msg}", file=sys.stderr)
    sys.stderr.flush()

try:
    log("Starting application initialization...")
    load_dotenv()
    log("Environment variables loaded.")

    from google import genai
    from db import get_supabase
    from booking_data import save_booking, load_bookings
    log("Internal modules imported.")

    app = Flask(__name__)
    log("Flask app instance created.")
    
    # Use a safe fallback for the secret key
    raw_secret = os.environ.get('SECRET_KEY', 'your_secret_key_here')
    if "os.secret_hex" in raw_secret:
        log("Warning: SECRET_KEY in env seems to be a code snippet, using default.")
        app.secret_key = "development_secret_key_fallback"
    else:
        app.secret_key = raw_secret

except Exception as e:
    log(f"CRITICAL ERROR DURING INITIALIZATION: {e}")
    import traceback
    log(traceback.format_exc())
    raise

# Initialize Gemini Client
# The client automatically picks up GEMINI_API_KEY from the environment
try:
    gemini_client = genai.Client()
except Exception as e:
    gemini_client = None
    print(f"Warning: Failed to initialize Gemini Client: {e}")

# Allowed public endpoints
PUBLIC_ENDPOINTS = ['home', 'about', 'services', 'contact', 'booking', 'login', 'static', 'chat']

@app.before_request
def require_login():
    if request.endpoint not in PUBLIC_ENDPOINTS and 'logged_in' not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('login', next=request.url))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        service = request.form.get('service')
        date = request.form.get('date')
        save_booking(name, email, phone_number, service, date)
        return render_template('booking_confirmation.html', name=name, email=email, service=service, date=date)
    return render_template('booking.html')


# Admin Dashboard Routes
@app.route('/dashboard')
def dashboard():
    bookings = load_bookings()
    recent_bookings = bookings[:5] if bookings else []
    return render_template('dashboard/index.html', bookings=bookings, recent_bookings=recent_bookings)

# View All Bookings
@app.route('/view-bookings')
def view_bookings():
    bookings = load_bookings()
    return render_template('dashboard/view_bookings.html', bookings=bookings)

# Blog Management
@app.route('/dashboard/blogs')
def blogs():
    try:
        supabase = get_supabase()
        res = supabase.table("blogs").select("*").order("created_at", desc=True).execute()
        blog_posts = res.data if res.data else []
    except Exception as e:
        blog_posts = []
        print(f"Error fetching blogs: {e}")
    return render_template('dashboard/blogs.html', blogs=blog_posts)

@app.route('/dashboard/blogs/new')
def new_blog():
    return render_template('dashboard/blog_editor.html')

@app.route('/dashboard/blogs/generate', methods=['POST'])
def generate_blog_content():
    if not gemini_client:
        return jsonify({"error": "AI service is currently unavailable."}), 503
        
    data = request.get_json()
    topic = data.get('topic', '')
    
    prompt = f"Write a professional blog post about {topic} for Insight Collective, an advisory firm. The tone should be strategic, insightful, and authoritative. Include a catchy title and formatted content with headings. Keep it under 800 words."
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return jsonify({"content": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/blogs/upload-image', methods=['POST'])
def upload_blog_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"error": "File type not allowed. Use: png, jpg, jpeg, gif, webp"}), 400
    
    try:
        supabase = get_supabase()
        # Generate a unique filename
        unique_name = f"blog-images/{uuid.uuid4().hex}.{ext}"
        file_bytes = file.read()
        
        # Upload to Supabase Storage bucket 'blog-assets'
        res = supabase.storage.from_('blog-assets').upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase.storage.from_('blog-assets').get_public_url(unique_name)
        
        return jsonify({"url": public_url})
    except Exception as e:
        print(f"Image upload error: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route('/dashboard/blogs/save', methods=['POST'])
def save_blog():
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    slug = data.get('slug', '').strip()
    featured_image = data.get('featured_image', '').strip()
    image_position = data.get('image_position', 'top')
    published = data.get('published', False)
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
    
    # Auto-generate slug if not provided
    if not slug:
        slug = title.lower().replace(' ', '-')[:60]
        # Remove special characters
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    
    try:
        supabase = get_supabase()
        blog_data = {
            "title": title,
            "slug": slug,
            "content": content,
            "image_url": featured_image,
            "published": published
        }
        res = supabase.table("blogs").insert(blog_data).execute()
        return jsonify({"success": True, "slug": slug, "data": res.data})
    except Exception as e:
        print(f"Blog save error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            supabase = get_supabase()
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                session['logged_in'] = True
                session['user_id'] = res.user.id
                flash("Successfully logged in!", "success")
                next_url = request.args.get('next')
                return redirect(next_url or url_for('view_bookings'))
        except Exception as e:
            flash(f"Invalid credentials or error logging in.", "danger")
            print(f"Login error: {e}")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/api/chat', methods=['POST'])
def chat():
    if not gemini_client:
        return jsonify({"error": "AI service is currently unavailable."}), 503
        
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
        
    user_message = data['message']
    
    system_prompt = "You are Insight AI, an intelligent assistant for Insight Collective, an advisory firm serving SMEs and visionary founders facing volatile markets. They act as Operational Architects providing Research Over Reaction, Disciplined Intelligence, and Coded Execution in Service areas: Intelligence & Positioning, Risk & Opportunity Mapping, and System Architecture. Be concise, professional, direct, and persuasive. Try not to generate extremely long responses. Keep it under 3 paragraphs."
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=system_prompt + "\n\nUser: " + user_message
        )
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"error": "Failed to generate AI response."}), 500

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
