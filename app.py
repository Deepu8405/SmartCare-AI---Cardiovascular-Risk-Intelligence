from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import hashlib
from datetime import datetime
import feedparser
from cachetools import TTLCache
import joblib
import numpy as np
import pandas as pd
import base64
import requests

import os
# ✅ SUPABASE CONFIG
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "smartcare-super-secret-2026")

# =========================
# Free health/news sources
# =========================
ARTICLE_FEEDS = [
    {
        "source": "WHO",
        "url": "https://www.who.int/rss-feeds/news-english.xml",
    },
    {
        "source": "CDC",
        "url": "https://tools.cdc.gov/api/v2/resources/media/132608.rss",
    },
]

# Cache: list + individual article lookup (avoid refetching every request)
ARTICLES_CACHE = TTLCache(maxsize=1, ttl=600)      # store latest list for 10 mins
ARTICLE_BY_ID_CACHE = TTLCache(maxsize=500, ttl=3600)  # store items for 1 hour
# ==================================Helper functions for news ====================
def _make_article_id(source: str, link: str) -> str:
    raw = f"{source}|{link}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def fetch_latest_articles(limit: int = 8):
    """
    Returns a list of dict articles:
    {id, source, title, link, summary, published}
    """
    if "latest" in ARTICLES_CACHE:
        return ARTICLES_CACHE["latest"][:limit]

    combined = []
    for feed in ARTICLE_FEEDS:
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries[:20]:
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", "") or getattr(e, "description", "")
            published = getattr(e, "published", "") or getattr(e, "updated", "")

            if not title or not link:
                continue

            aid = _make_article_id(feed["source"], link)
            item = {
                "id": aid,
                "source": feed["source"],
                "title": title,
                "link": link,
                "summary": summary,
                "published": published
            }
            combined.append(item)
            ARTICLE_BY_ID_CACHE[aid] = item

    # Sort by published string best-effort (feeds differ)
    # If parsing fails, keep original order
    def sort_key(a):
        try:
            dt = feedparser._parse_date(a["published"])
            if dt:
                return datetime(*dt[:6])
        except Exception:
            pass
        return datetime(1970, 1, 1)

    combined.sort(key=sort_key, reverse=True)

    ARTICLES_CACHE["latest"] = combined
    return combined[:limit]
# -----------------------------------helper function for news end-----------------------------
# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/')
def index():
    articles = fetch_latest_articles(limit=6)
    return render_template('index.html', articles=articles)

@app.route('/article/<article_id>')
def article_view(article_id):
    article = ARTICLE_BY_ID_CACHE.get(article_id)

    # if not in cache (server restarted), refetch once
    if not article:
        fetch_latest_articles(limit=20)
        article = ARTICLE_BY_ID_CACHE.get(article_id)

    if not article:
        return "Article not found (cache expired). Go back and click again.", 404

    return render_template("article.html", article=article)
# ------------------------- article route above -------------------------
# //  ================================ml model pridection ================================
# ---- Helper functions
import pandas as pd
import numpy as np
import joblib

# --- CONSTANTS (Must match your Training Script) ---
AGE_ORDER = [
    'Age 18 to 24', 'Age 25 to 29', 'Age 30 to 34', 'Age 35 to 39',
    'Age 40 to 44', 'Age 45 to 49', 'Age 50 to 54', 'Age 55 to 59',
    'Age 60 to 64', 'Age 65 to 69', 'Age 70 to 74', 'Age 75 to 79', 'Age 80 or older'
]

# EXACT order and naming from your successful training run
SELECTED_FEATURES = [
    'HadAngina', 'Comorbidity_Count', 'Angina_Age_Risk', 'RemovedTeeth', 
    'PhysicalActivities', 'ChestScan', 'GeneralHealth', 'AlcoholDrinkers', 
    'FluVaxLast12', 'Sex', 'PneumoVaxEver', 'RaceEthnicityCategory', 
    'LastCheckupTime', 'SmokerStatus', 'HadArthritis', 'DifficultyWalking', 
    'SleepHours', 'TetanusLast10Tdap', 'HadStroke', 'HadDiabetes'
]

def input_to_df(form_data):
    """Converts raw form data to a DataFrame with necessary columns for engineering."""
    age = int(form_data.get('age', 0))
    if age >= 80: age_cat = 'Age 80 or older'
    elif age >= 75: age_cat = 'Age 75 to 79'
    elif age >= 70: age_cat = 'Age 70 to 74'
    elif age >= 65: age_cat = 'Age 65 to 69'
    elif age >= 60: age_cat = 'Age 60 to 64'
    elif age >= 55: age_cat = 'Age 55 to 59'
    elif age >= 50: age_cat = 'Age 50 to 54'
    elif age >= 45: age_cat = 'Age 45 to 49'
    elif age >= 40: age_cat = 'Age 40 to 44'
    elif age >= 35: age_cat = 'Age 35 to 39'
    elif age >= 30: age_cat = 'Age 30 to 34'
    elif age >= 25: age_cat = 'Age 25 to 29'
    else: age_cat = 'Age 18 to 24'

    # Map all binary fields to 0 or 1
    raw_data = {
        'AgeCategory': age_cat,
        'Sex': form_data.get('Sex'),
        'GeneralHealth': form_data.get('GeneralHealth'),
        'HadAngina': int(form_data.get('HadAngina', 0)),
        'HadStroke': int(form_data.get('HadStroke', 0)),
        'HadDiabetes': int(form_data.get('HadDiabetes', 0)),
        'HadCOPD': int(form_data.get('HadCOPD', 0)),
        'HadArthritis': int(form_data.get('HadArthritis', 0)),
        'SmokerStatus': form_data.get('SmokerStatus'),
        'SleepHours': float(form_data.get('SleepHours', 7)),
        'PhysicalActivities': int(form_data.get('PhysicalActivities', 0)),
        'DifficultyWalking': int(form_data.get('DifficultyWalking', 0)),
        'RemovedTeeth': form_data.get('RemovedTeeth'),
        'ChestScan': int(form_data.get('ChestScan', 0)),
        'RaceEthnicityCategory': form_data.get('RaceEthnicityCategory'),
        'LastCheckupTime': form_data.get('LastCheckupTime'),
        'FluVaxLast12': int(form_data.get('FluVaxLast12', 0)),
        'PneumoVaxEver': int(form_data.get('PneumoVaxEver', 0)),
        'TetanusLast10Tdap': form_data.get('TetanusLast10Tdap'),
        'AlcoholDrinkers': int(form_data.get('AlcoholDrinkers', 0))
    }
    return pd.DataFrame([raw_data])

def preprocess_for_model(df, scaler, encoders):
    """Engineers features and scales data using saved .pkl files."""
    df_proc = df.copy()

    # 1. ENGINEER POWER FEATURES
    df_proc['Age_Code'] = pd.Categorical(df_proc['AgeCategory'], categories=AGE_ORDER).codes
    df_proc['Angina_Age_Risk'] = df_proc['HadAngina'] * df_proc['Age_Code']
    
    # Comorbidity Count (uses HadCOPD which is later dropped from the final 20)
    comorbid_cols = ['HadAngina', 'HadArthritis', 'HadDiabetes', 'HadCOPD', 'HadStroke']
    df_proc['Comorbidity_Count'] = df_proc[comorbid_cols].sum(axis=1)

    # 2. LABEL ENCODING (Categorical Strings -> Numbers)
    for col, le in encoders.items():
        val = str(df_proc[col].iloc[0])
        # Safety: If UI sends something the model hasn't seen, default to first category
        if val not in le.classes_:
            df_proc[col] = le.transform([le.classes_[0]])
        else:
            df_proc[col] = le.transform([val])

    # 3. ALIGNMENT & SCALING
    # Filter to the exact 20 features in the exact order required by the model
    X_final = df_proc[SELECTED_FEATURES]
    
    # Scale using the training Mean and StdDev
    return scaler.transform(X_final)

# --- LOAD MODELS & SCALER ---
# Use joblib for both as they are picklable
scaler = joblib.load(os.path.join('models', 'scaler.pkl'))
rf_model = joblib.load(os.path.join('models', 'rf_component.pkl'))
xgb_model = joblib.load(os.path.join('models', 'xgb_components.pkl'))
encoders = joblib.load(os.path.join('models', 'encoders.pkl'))

# Load the medical threshold (used for High/Low risk classification)
try:
    # Fix the path here as well
    with open(os.path.join('models', 'threshold.txt'), 'r') as f:
        OPTIMAL_THRESHOLD = float(f.read().strip())
except Exception as e:
    print(f"Threshold load error: {e}")
    OPTIMAL_THRESHOLD = 0.5

@app.route('/how-to-use')
def how_to_use():
    return render_template('how-to-use.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # 1. Get Form Data & Convert to DF
        data = request.form.to_dict()
        df_input = input_to_df(data)
        
        # 2. Preprocess (Engineering + Encoding + Scaling)
        # scaler and encoders should be loaded at the top of app.py using joblib
        processed_input = preprocess_for_model(df_input, scaler, encoders)
        
        # 3. Get Probabilities from Both Ensemble Components
        prob_rf = rf_model.predict_proba(processed_input)[:, 1][0]
        prob_xgb = xgb_model.predict_proba(processed_input)[:, 1][0]
        
        # 4. Final Risk (Average of 2 Models)
        final_risk_score = (prob_rf + prob_xgb) / 2
        session["last_risk_percent"] = float(final_risk_score)  # e.g., 23.45

        # 5. Return HTML Fragment to HTMX
        return render_template('result.html', 
                               risk_score=final_risk_score,
                               threshold=0.5,  # Update based on your threshold.txt
                               patient_data=data)
                               
    except Exception as e:
        print(f"Prediction Error: {e}")
        return "<div class='p-4 bg-red-100 text-red-700 rounded-2xl'>Internal processing error.</div>"
    
# def get_ensemble_prediction(from_data):

# //  ================================ end ml model pridection ================================
@app.route('/login', methods=['GET', 'POST'])  # ← BOTH GET + POST!
def login():
    if request.method == 'POST':
        username = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        

        if username == 'admin' and password == '1234':
            session['user'] = username
            return '''
            <div class="bg-green-100 border-2 border-green-400 rounded-2xl p-8 text-center shadow-2xl mx-auto max-w-md">
                <div class="text-3xl mb-6">✅ LOGIN SUCCESS!</div>
                <div class="text-xl text-green-800 font-bold mb-6">Welcome, Admin 👋</div>
                <a href="/" class="block w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 px-8 rounded-2xl font-black text-lg shadow-xl hover:from-green-700 hover:to-emerald-700 transition-all">
                    🚀 Enter Dashboard
                </a>
            </div>
            '''
        
        try:
            res=supabase.auth.sign_in_with_password({
                "email":username,
                "password":password
            })
             
            # Save tokens in Flask session (optional but useful later)
            session["sb_access_token"] = res.session.access_token
            session["sb_refresh_token"] = res.session.refresh_token
           # ✅ store uuid for saving records
            session["user_id"] = res.user.id if res.user else None

            # ✅ keep display name for navbar
            session["user"] = (res.user.email.split("@")[0] if res.user and res.user.email else "User")
            # Display name in navbar:
            user_email=res.user.email if res.user else username
            meta=getattr(res.user,"user_metadata",None) or {}
            display=meta.get("first_name") or user_email.split("@")[0]
            session["user"]=display

            response=dict(supabase.auth.get_user(session["sb_access_token"]).user)

            # update user_data_table for new user records
            response=supabase.table("user_data").update({
                "first_name":display,
                "last_name":meta.get("last_name")or""
            }).eq("uuid",response['id']).execute()
          
            return '''
            <div class="bg-green-100 border-2 border-green-400 rounded-2xl p-8 text-center shadow-2xl mx-auto max-w-md">
                <div class="text-3xl mb-6">✅ LOGIN SUCCESS!</div>
                <div class="text-xl text-green-800 font-bold mb-6">Welcome 👋</div>
                <a href="/" class="block w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 px-8 rounded-2xl font-black text-lg shadow-xl hover:from-green-700 hover:to-emerald-700 transition-all">
                    🚀 Enter Dashboard
                </a>
            </div>
            '''
        except Exception as e:
            return f'''
            <div class="bg-red-100 border-2 border-red-400 rounded-2xl p-8 text-center shadow-2xl mx-auto max-w-md">
                <div class="text-3xl mb-6">❌ LOGIN FAILED</div>
                <div class="text-sm text-red-800 font-semibold">{str(e)}</div>
            </div>
            ''', 401            
       
           
    
    # GET request = show login page
    return render_template('login.html')


@app.route('/signup', methods=['POST'])
def signup():
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm = request.form.get('confirm_password', '').strip()

    if password != confirm:
        # ✅ return 200 so HTMX shows it
        return '''
        <div class="bg-red-100 border-2 border-red-400 rounded-3xl p-6 text-center shadow-xl">
            <div class="text-xl font-bold text-red-800">❌ Passwords do not match</div>
        </div>
        '''

    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "first_name": first_name,
                    "last_name": last_name
                }
            }
        })

        # If email confirm ON, session may be None
        if getattr(res, "session", None):
            session["sb_access_token"] = res.session.access_token
            session["sb_refresh_token"] = res.session.refresh_token
            session["user"] = first_name or email.split("@")[0]

            return f'''
            <div class="bg-emerald-100 border-2 border-emerald-400 rounded-3xl p-6 text-center shadow-xl">
                <div class="text-2xl font-black text-emerald-800">✅ Signup Success!</div>
                <div class="text-sm text-emerald-700 mt-2">Welcome {first_name or email} 👋</div>
                <a href="/" class="inline-block mt-4 bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-6 py-3 rounded-2xl font-bold shadow-lg">
                    Enter Dashboard
                </a>
            </div>
            '''

        return '''
        <div class="bg-emerald-100 border-2 border-emerald-400 rounded-3xl p-6 text-center shadow-xl">
            <div class="text-xl font-bold text-emerald-800">✅ Account created</div>
            <div class="text-sm text-emerald-700 mt-2">
              Check your email to confirm, then login.
            </div>
            <a href="/login" class="inline-block mt-4 bg-gradient-to-r from-blue-600 to-emerald-600 text-white px-6 py-3 rounded-2xl font-bold shadow-lg">
                Go to Login
            </a>
        </div>
        '''
    except Exception as e:
        print("❌ SUPABASE SIGNUP ERROR:", str(e))  # ✅ shows in terminal

        # ✅ return 200 so HTMX shows it
        return f'''
        <div class="bg-red-100 border-2 border-red-400 rounded-3xl p-6 text-center shadow-xl">
            <div class="text-xl font-bold text-red-800">❌ Signup Failed</div>
            <div class="text-sm text-red-700 mt-2">{str(e)}</div>
        </div>
        '''



@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    # ✅ HTMX: Update ONLY navbar → NO full page reload!
    return '''
    <div id="auth-nav" data-auth="0" class="flex items-center space-x-4">
        <a href="/login" class="bg-gradient-to-r from-blue-600 to-emerald-600 text-white px-8 py-3 rounded-2xl font-bold shadow-xl hover:from-blue-700 hover:to-emerald-700 transform hover:-translate-y-0.5 transition-all duration-300">
            🔐 Login
        </a>
    </div>
    '''



# =========================== ai agent ===================================


# import google.generativeai as genai
from flask import Response, stream_with_context
from google import genai
import markdown as md
import bleach

# Initialize Gemini
# def get_assistant_response(user_message, api_key, report_link=None, risk=None, thread_id=None):
#     client = genai.Client(api_key=api_key)
# client=genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
# MODEL = "gemini-3-flash-preview"
MODEL = "gemini-2.5-flash"


def render_ai_markdown(text: str) -> str:
    # Convert markdown to HTML
    html = md.markdown(
        text or "",
        extensions=["extra", "sane_lists", "tables"]
    )

    # Sanitize (important)
    allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union({
        "p", "br", "ul", "ol", "li", "strong", "em",
        "h1", "h2", "h3", "blockquote",
        "table", "thead", "tbody", "tr", "th", "td"
    })
    allowed_attrs = {
        **bleach.sanitizer.ALLOWED_ATTRIBUTES,
        "a": ["href", "title", "target", "rel"],
        "th": ["colspan", "rowspan"],
        "td": ["colspan", "rowspan"]
    }

    clean = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    return clean

def get_user_latest_report(user_id):
    """Fetches the latest report URL from the user_report table."""
    try:
        res = supabase.table("report_link").select("report_link").eq("uuid", user_id).order("created_at", desc=True).limit(1).execute()
        if res.data:
            print("report fetched")
            return res.data[0]['report_link']
    except Exception as e:
        print(f"Error fetching report: {e}")
    return None

def fetch_pdf_as_base64(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return base64.b64encode(r.content).decode("utf-8")

def get_assistant_response(user_text: str,api_key:str,report_link: str | None,risk:float , user_id: str) -> str:
   
    client = genai.Client(api_key=api_key)
    """
    AI Assistant Response Logic:
    1. NO REPORT + NO RISK SCORE → "Upload report or use risk calculator"
    2. RISK SCORE ONLY → Include risk score context  
    3. REPORT LINK → Attach PDF to Gemini
    4. Graceful fallbacks everywhere
    """
    doc_part = None
    if report_link:
        try:
            pdf_b64 = fetch_pdf_as_base64(report_link)
            doc_part = {"type": "document", "data": pdf_b64, "mime_type": "application/pdf"}
        except Exception as e:
            # If URL fetch fails, proceed without report (or return a helpful message)
            doc_part = None

    # 1. Get thread_id (safe)
    thread_id = ""
    try:
        th = supabase.table("user_data").select("thread_id").eq("uuid", user_id).limit(1).execute()
        if th.data and th.data[0].get("thread_id"):
            thread_id = th.data[0]["thread_id"]
            print("✅ Thread_id found:", thread_id)
    except Exception as e:
        print("❌ thread_id fetch error:", e)
        thread_id = ""
    
    # 2. Get risk score from session (safe)
    risk_score = session.get("last_risk_percent", None)
    
    # 3. Build smart context message
    context_parts = []
    
    if not report_link and not risk_score:
        # CASE 1: No report + No risk score
        return """🤖 AI Doctor Assistant

To give you personalized medical advice, please:

1️⃣ **Upload a medical report** (PDF/JPG) for automatic analysis
2️⃣ **Use the heart risk calculator** above to get your risk score

Once you have either, I can provide specific recommendations! 💙"""

    if risk_score:
        # CASE 2: Risk score available
        risk_pct = risk_score * 100
        context_parts.append(f"Patient's latest heart risk score: **{risk_pct:.1f}%**")
    
    if report_link:
        # CASE 3: Report available (will be attached separately)
        context_parts.append("Patient has uploaded medical report (attached)")
    
    # 4. Main prompt with context
    system_prompt = f"""
        You are a cardiologist AI assistant. 
            
        Patient Context: {', '.join(context_parts) if context_parts else 'No medical data available yet'}

        User Question: "{user_text}"

        Provide specific, evidence-based advice. Be empathetic and clear.
        """
    inputs = [{"type": "text", "text": system_prompt}]
    if doc_part:
        inputs.append(doc_part)
    use_prev = False if doc_part else bool(thread_id)

    inputs.append({"type": "text", "text": user_text})
    print("DOC_PART_KEYS:", list(doc_part.keys()) if doc_part else None)
    print("HAS_URI_IN_INPUTS:", any(isinstance(x, dict) and x.get("uri") for x in inputs))

    resp = client.interactions.create(
                model=MODEL,
                input=inputs,
                previous_interaction_id=thread_id if use_prev else None
            )
    print(resp)
    # 5. Save thread_id for future
    interaction_id = getattr(resp, "id", None)
    if interaction_id:
        supabase.table("user_data").update({"thread_id": interaction_id}).eq("uuid", user_id).execute()
        
    response_text = getattr(resp.outputs[-1], "text", "Sorry, I couldn't process that request") if resp.outputs else "No response generated"
    print("🤖 AI Response:", response_text[:100] + "...")
    # print(response_text)
    return response_text


@app.route('/chat', methods=['POST'])
def chat():
    user_text = request.form.get('message', '').strip()
    api_key = request.form.get("api_key", "").strip()
    if not api_key:
        return '''
        <div class="p-4 bg-yellow-100 rounded-xl">
        🔑 Please enter your Gemini API key to use the assistant.
        </div>
        '''

    if not user_text:
        return ""
    
    user_id = session.get("user_id")
    report_link = get_user_latest_report(user_id)
    
    # response = get_assistant_response(report_link, user_text, user_id)
    # get_assistant_response(user_text: str,api_key:str,report_link: str | None,risk:float , user_id: str)
    response = get_assistant_response(
            user_text=user_text,
            api_key=api_key,
            report_link=report_link,
            risk=session.get('risk') if session.get('risk') else 0.0,
            user_id=session.get('user_id') if session.get('user_id') else ""
        )

    formated_text=render_ai_markdown(response)
    
    # Return formatted HTML response
    return f'''
    <div class="p-6 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-2xl max-w-md shadow-2xl border-4 border-white/20 mb-4">
        <div class="flex items-start gap-3">
            <div class="w-10 h-10 bg-white/20 rounded-2xl flex items-center justify-center flex-shrink-0 mt-1">
                <span class="text-lg font-bold">🤖</span>
            </div>
            <div class="flex-1">
                <div class="font-bold text-lg mb-2 flex items-center gap-2">AI Doctor Assistant</div>
                <div class="text-sm leading-relaxed">{formated_text}</div>
            </div>
        </div>
    </div>
    '''

# =========================== ai agent end  ===================================
# ----------------------------------------- report process -----------------------
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from flask import request, session

@app.route('/upload-report', methods=['POST'])
def upload_report():
    if 'user' not in session:
        return '🔐 Login required', 401

    file = request.files.get('file')
    if not file or file.filename == '':
        return 'No file selected', 400

    # Use whatever you consider "username"
    # Safer: use uuid user_id to avoid special chars.
    user_id = session.get("user_id")
    username = session.get("user")  # if this is email, it may contain "@"
    user_folder = str(user_id) if user_id else str(username)

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Optional: restrict file types
    allowed = {"pdf", "jpg", "jpeg", "png"}
    if ext and ext not in allowed:
        return "Unsupported file type. Upload PDF/JPG/PNG only.", 400

    # Unique name prevents 409 conflicts
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex}-{filename}"
    file_path = f"{user_folder}/{unique_name}"

    bucket = supabase.storage.from_("reports")
    data = file.read()

    # Upload into "folder"
    bucket.upload(file_path, data)

    # Signed URL (example: 24 hours)
    signed = bucket.create_signed_url(file_path, 24 * 3600)
    report_url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
    if not report_url:
        return "Upload succeeded but failed to create signed URL.", 500

    # Save each report row (history) into user_report table
    # Adjust column names to match your schema:
    supabase.table("report_link").insert({
        "uuid": user_id,               # or "user_id" depending on your table
        "report_link": report_url,     # the signed URL you want Gemini to use
    }).execute()

    return f'✅ {filename} uploaded!'



# ---------- upload user data to supabase  ----------------------
import ast
import json
from flask import jsonify, request, session
@app.route('/save-patient-data', methods=['POST'])
def save_record():
    # ✅ Strong auth check
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401


    try:
        payload = request.get_json() or {}

        risk_str = payload.get("risk", "0%")
        raw = payload.get("data", {})

        # If raw is JSON string, parse it
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                # fallback for single-quote dict string
                raw = ast.literal_eval(raw)

        if not isinstance(raw, dict):
            return jsonify({"status": "error", "message": "Invalid patient data payload"}), 400

        # ----------------------------
        # Helpers
        # ----------------------------
        def to_int(v, default=0):
            try:
                if v is None or v == "":
                    return default
                return int(float(v))
            except Exception:
                return default

        def to_float(v, default=0.0):
            try:
                if v is None or v == "":
                    return default
                return float(v)
            except Exception:
                return default

        def parse_percent(s):
            try:
                s = str(s).strip()
                return float(s.replace("%", ""))
            except Exception:
                return 0.0

        # ----------------------------
        # Compute engineered features server-side
        # ----------------------------
        # NOTE: This matches preprocess_for_model logic
        age_category = raw.get("AgeCategory")
        try:
            age_code = AGE_ORDER.index(age_category) if age_category in AGE_ORDER else 0
        except Exception:
            age_code = 0

        had_angina = to_int(raw.get("HadAngina", 0))
        had_stroke = to_int(raw.get("HadStroke", 0))
        had_diabetes = to_int(raw.get("HadDiabetes", 0))
        had_copd = to_int(raw.get("HadCOPD", 0))
        had_arthritis = to_int(raw.get("HadArthritis", 0))

        comorbidity_count = had_angina + had_arthritis + had_diabetes + had_copd + had_stroke
        angina_age_risk = had_angina * age_code

        # ----------------------------
        # Build DB row
        # ----------------------------
        data = {
            "user_id": session.get("user_id"),
            "risk_percentage": parse_percent(risk_str),

            # Numeric/Binary Features
            "had_angina": had_angina,
            "had_stroke": had_stroke,
            "had_diabetes": had_diabetes,
            "had_copd": had_copd,
            "had_arthritis": had_arthritis,
            "physical_activities": to_int(raw.get("PhysicalActivities", 0)),
            "alcohol_drinkers": to_int(raw.get("AlcoholDrinkers", 0)),
            "chest_scan": to_int(raw.get("ChestScan", 0)),
            "flu_vax_last_12": to_int(raw.get("FluVaxLast12", 0)),
            "pneumo_vax_ever": to_int(raw.get("PneumoVaxEver", 0)),
            "difficulty_walking": to_int(raw.get("DifficultyWalking", 0)),
            "sleep_hours": to_float(raw.get("SleepHours", 0)),

            # Categorical Features
            "sex": raw.get("Sex"),
            "general_health": raw.get("GeneralHealth"),
            "removed_teeth": raw.get("RemovedTeeth"),
            "race_ethnicity": raw.get("RaceEthnicityCategory"),
            "last_checkup": raw.get("LastCheckupTime"),
            "smoker_status": raw.get("SmokerStatus"),
            "tetanus_last_10_tdap": raw.get("TetanusLast10Tdap"),

            # ✅ Engineered Features (computed server-side)
            "comorbidity_count": comorbidity_count,
            "angina_age_risk": angina_age_risk,
        }

        # Optional (highly recommended): store raw input for debugging/auditing
        # Add a jsonb column in patient_records called raw_payload if you want this:
        # data["raw_payload"] = raw

        supabase.table("patient_records").insert(data).execute()

        return jsonify({"status": "success", "message": "Record synced successfully"})

    except Exception as e:
        print(f"❌ Supabase Sync Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

    
if __name__ == '__main__':
    app.run(debug=True, port=5000)
