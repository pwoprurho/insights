import os
import uuid
import csv
import io
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# Enable CORS
CORS(app)

# Lazy client initialization
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai
            _gemini_client = genai.Client()
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini Client: {e}")
    return _gemini_client

# Allowed public endpoints
PUBLIC_ENDPOINTS = ['home', 'about', 'services', 'insights', 'blog_detail', 'contact', 'booking', 'login', 'forgot_password', 'static', 'chat', 'health']

@app.before_request
def require_login():
    # Zero Trust: Explicitly verify authentication for non-public endpoints
    if request.endpoint and request.endpoint not in PUBLIC_ENDPOINTS:
        if not session.get('logged_in'):
            # Return strict 401 for API/JSON context instead of a leaky redirect
            if request.is_json or request.path.startswith('/api/') or request.method in ['POST', 'PUT', 'DELETE']:
                return jsonify({"error": "Unauthorized access. Zero trust policy enforced."}), 401
            
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/insights')
def insights():
    try:
        from supabase_client import supabase
        res = supabase.table("blogs").select("*").eq("published", True).order("created_at", desc=True).execute()
        blog_posts = res.data if res.data else []
    except Exception as e:
        blog_posts = []
        print(f"Error fetching blogs for insights: {e}")
    return render_template('insights.html', blogs=blog_posts)

@app.route('/insights/<slug>')
def blog_detail(slug):
    try:
        from supabase_client import supabase
        res = supabase.table("blogs").select("*").eq("slug", slug).eq("published", True).execute()
        if res.data and len(res.data) > 0:
            return render_template('blog_detail.html', post=res.data[0])
    except Exception as e:
        print(f"Error fetching blog detail: {e}")
    flash("Blog post not found.", "warning")
    return redirect(url_for('insights'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        from booking_data import save_booking
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        service = request.form.get('service') # Engagement Type
        company = request.form.get('company')
        business_description = request.form.get('business_description')
        challenge = request.form.get('challenge')
        timeline = request.form.get('timeline')
        source = request.form.get('source')
        
        save_booking(
            name=name, 
            email=email, 
            phone_number=phone_number, 
            service=service, 
            company=company,
            business_description=business_description,
            challenge=challenge,
            timeline=timeline,
            source=source
        )
        return render_template('booking_confirmation.html', name=name, email=email, service=service)
    return render_template('booking.html')


# Admin Dashboard Routes
@app.route('/dashboard')
def dashboard():
    from booking_data import load_bookings
    bookings = load_bookings()
    recent_bookings = bookings[:5] if bookings else []
    
    # Fetch blog count
    blog_count = 0
    try:
        from supabase_client import supabase
        res = supabase.table("blogs").select("id", count="exact").execute()
        blog_count = res.count if res.count is not None else 0
    except Exception as e:
        print(f"Error fetching blog count: {e}")
        
    return render_template('dashboard/index.html', bookings=bookings, recent_bookings=recent_bookings, blog_count=blog_count)

# View All Bookings
@app.route('/view-bookings')
def view_bookings():
    from booking_data import load_bookings
    bookings = load_bookings()
    return render_template('dashboard/view_bookings.html', bookings=bookings)

# Blog Management
@app.route('/dashboard/blogs')
def blogs():
    try:
        from supabase_client import supabase
        # Use singleton supabase client
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
    client = get_gemini_client()
    if not client:
        return jsonify({"error": "AI service is currently unavailable."}), 503
        
    data = request.get_json()
    topic = data.get('topic', '')
    
    prompt = f"Write a premium institutional research report about {topic} for Insight Collective. The brand philosophy is 'Research over Reaction' and 'Structural Intelligence'. Tone: Strategic, authoritative, intellectual, and architectural. The output should be a structured executive-style report with a compelling title and clear headings. Keep it under 800 words."
    
    try:
        response = client.models.generate_content(
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
        from supabase_client import supabase
        # Generate a unique filename
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # 1. Local Fallback (always save a copy locally in case Supabase fails)
        local_dir = os.path.join(app.root_path, 'static', 'uploads', 'blog-images')
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        file.seek(0)
        file.save(local_path)
        
        # Default to local URL
        public_url = url_for('static', filename=f'uploads/blog-images/{filename}', _external=True)
        
        # 2. Try Supabase Storage
        file.seek(0)
        file_bytes = file.read()
        res = supabase.storage.from_('blog-assets').upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        # If successful, use the Supabase public URL instead
        public_url = supabase.storage.from_('blog-assets').get_public_url(filename)
            
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
        from supabase_client import supabase
        # Use singleton supabase client
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

@app.route('/dashboard/blogs/edit/<blog_id>')
def edit_blog(blog_id):
    try:
        from supabase_client import supabase
        res = supabase.table("blogs").select("*").eq("id", blog_id).execute()
        if res.data and len(res.data) > 0:
            return render_template('dashboard/blog_editor.html', blog=res.data[0])
    except Exception as e:
        print(f"Error fetching blog for edit: {e}")
    flash("Blog post not found.", "danger")
    return redirect(url_for('blogs'))

@app.route('/dashboard/blogs/update', methods=['POST'])
def update_blog():
    data = request.get_json()
    blog_id = data.get('id')
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    slug = data.get('slug', '').strip()
    featured_image = data.get('featured_image', '').strip()
    image_position = data.get('image_position', 'top')
    published = data.get('published', False)
    
    if not blog_id or not title or not content:
        return jsonify({"error": "ID, title and content are required"}), 400
    
    try:
        from supabase_client import supabase
        blog_data = {
            "title": title,
            "slug": slug,
            "content": content,
            "image_url": featured_image,
            "published": published
        }
        res = supabase.table("blogs").update(blog_data).eq("id", blog_id).execute()
        return jsonify({"success": True, "slug": slug, "data": res.data})
    except Exception as e:
        print(f"Blog update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/blogs/delete/<blog_id>', methods=['POST'])
def delete_blog(blog_id):
    try:
        from supabase_client import supabase
        supabase.table("blogs").delete().eq("id", blog_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Blog delete error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/blogs/toggle/<blog_id>', methods=['POST'])
def toggle_blog(blog_id):
    try:
        from supabase_client import supabase
        # Fetch current status
        res = supabase.table("blogs").select("published").eq("id", blog_id).execute()
        if not res.data:
            return jsonify({"error": "Blog not found"}), 404
        current = res.data[0]['published']
        # Toggle
        supabase.table("blogs").update({"published": not current}).eq("id", blog_id).execute()
        return jsonify({"success": True, "published": not current})
    except Exception as e:
        print(f"Blog toggle error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/bookings/export')
def export_bookings():
    from booking_data import load_bookings
    bookings = load_bookings()
    
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date', 'Name', 'Email', 'Phone', 'Company', 'Service', 'Challenge', 'Timeline', 'Source'])
    for b in bookings:
        writer.writerow([
            b.get('created_at', '')[:10] if b.get('created_at') else '',
            b.get('name', ''),
            b.get('email', ''),
            b.get('phone_number', ''),
            b.get('company', ''),
            b.get('service', ''),
            b.get('challenge', ''),
            b.get('timeline', ''),
            b.get('source', '')
        ])
    
    output = si.getvalue()
    from flask import Response
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bookings_export.csv'}
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Local Development Fallback
            if email == "akporurho@proton.me" and password == "@mure3nny":
                session['logged_in'] = True
                session['user_id'] = 'dev-admin-id'
                flash("Logged in via Development Fallback (Supabase Unreachable)", "info")
                return redirect(url_for('view_bookings'))

            from supabase_client import supabase
            # Use singleton supabase client
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                session['logged_in'] = True
                session['user_id'] = res.user.id
                flash("Successfully logged in!", "success")
                next_url = request.args.get('next')
                return redirect(next_url or url_for('view_bookings'))
        except Exception as e:
            # Emergency Fallback if Supabase fails (DNS/Offline)
            error_msg = str(e).lower()
            if "getaddrinfo" in error_msg or "dns" in error_msg or "network is unreachable" in error_msg:
                if email == "akporurho@proton.me" and password == "@mure3nny":
                    session['logged_in'] = True
                    session['user_id'] = 'dev-admin-id'
                    flash("Logged in via Emergency Fallback (DNS Failure Detected)", "warning")
                    return redirect(url_for('view_bookings'))
                else:
                    flash("Network Error: Supabase is unreachable. You must use the developer fallback account (akporurho@proton.me / @mure3nny) to log in.", "danger")
                    return redirect(url_for('login'))
                
            flash(f"Login failed: {str(e)}", "danger")
            print(f"Login error: {e}")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            from supabase_client import supabase
            res = supabase.auth.sign_up({"email": email, "password": password})
            flash("New admin registered successfully! They must confirm their email before logging in.", "success")
            return redirect(url_for('register'))
        except Exception as e:
            # Emergency Fallback if Supabase fails (DNS/Offline)
            error_msg = str(e).lower()
            if "getaddrinfo" in error_msg or "dns" in error_msg or "network is unreachable" in error_msg:
                flash("Network Error: Registration simulated via DNS Fallback because Supabase is unreachable.", "info")
                return redirect(url_for('register'))
                
            flash(f"Register failed: {str(e)}", "danger")
            print(f"Registration error: {e}")
            
    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        try:
            from supabase_client import supabase
            res = supabase.auth.reset_password_email(email)
            flash("If that email exists, a reset link has been sent.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            # Emergency Fallback if Supabase fails (DNS/Offline)
            if "getaddrinfo" in str(e).lower() or "dns" in str(e).lower():
                flash("Password reset email simulated via DNS Fallback. Check your local logs.", "info")
                return redirect(url_for('login'))
                
            flash(f"Error requesting password reset: {e}", "error")
            print(f"Password reset error: {e}")
            
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/api/chat', methods=['POST'])
def chat():
    client = get_gemini_client()
    if not client:
        return jsonify({"error": "AI service is currently unavailable."}), 503
        
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
        
    user_message = data['message']
    
    system_prompt = (
        "You are Institutional AI, the primary intelligence assistant for Insight Collective, a systems architecture firm. "
        "Insight Collective provides structural intelligence for high-growth SMEs and visionaries in volatile markets. "
        "Our philosophy is 'Research over Reaction' and 'Disciplined Intelligence.' "
        "Engagements are selective and strategic. We help businesses close the 'Infrastructure Gap.' "
        "Be authoritative, precise, direct, and intellectually grounded. Avoid generic assistance. "
        "Direct users toward 'Strategic Engagement' for high-touch needs. Keep responses concise and structured."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=system_prompt + "\n\nUser: " + user_message
        )
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"error": "Failed to generate AI response."}), 500

if __name__ == '__main__':
    print("[READY] Fadav Elite Group Command Center Starting...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
