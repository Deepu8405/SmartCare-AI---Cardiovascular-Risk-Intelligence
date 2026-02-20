import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import plotly
import plotly.graph_objs as go
from flask import Flask, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
import google.generativeai as genai

# 1. Load Environment Variables
load_dotenv()

app = Flask(__name__)

# 2. Configuration & Client Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("--- SmartCare Environment Check ---")
print(f"Numpy: {np.__version__}")
print(f"Pandas: {pd.__version__}")
print(f"XGBoost: {xgb.__version__}")
print(f"Flask: {Flask.__module__}") # Simple check

# Initialize Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase Client: Initialized")
    except Exception as e:
        print(f"❌ Supabase Client Error: {e}")
else:
    print("⚠️ Supabase Credentials missing in .env")

# Initialize OpenAI
# openai_client = None
# if OPENAI_API_KEY:
#     try:
#         openai_client = OpenAI(api_key=OPENAI_API_KEY)
#         print("✅ OpenAI Client: Initialized")
#     except Exception as e:
#         print(f"❌ OpenAI Client Error: {e}")
# else:
#     print("⚠️ OpenAI API Key missing in .env")


# Initialize Gemini
# Initialize Gemini with model check
gemini_client = None
if os.getenv("GOOGLE_AI_API_KEY"):
    try:
        genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        
        # List available models first
        print("Available Gemini models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
        
        # Use first available model (safe fallback)
        available_models = [m for m in genai.list_models() 
                          if 'generateContent' in m.supported_generation_methods]
        if available_models:
            model_name = available_models[0].name  # Auto-detect working model
            gemini_client = genai.GenerativeModel(model_name)
            print(f"✅ Gemini Client: Using {model_name}")
        else:
            print("❌ No generateContent models found")
            
    except Exception as e:
        print(f"❌ Gemini Client Error: {e}")

# --- Routes for Testing ---

@app.route('/')
def home():
    """Root endpoint to check if Flask is running."""
    return jsonify({
        "status": "online",
        "project": "SmartCare Diagnostic",
        "versions": {
            "pandas": pd.__version__,
            "xgboost": xgb.__version__,
            "openai_lib": "2.16.0" # Based on your list
        }
    })

@app.route('/test-ml')
def test_ml():
    """Tests XGBoost, Pandas, and Numpy integration."""
    try:
        # Create dummy training data
        df = pd.DataFrame(np.random.rand(10, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
        labels = np.random.randint(2, size=10)
        
        # Train a tiny XGBoost model
        model = xgb.XGBClassifier(n_estimators=2, max_depth=2)
        model.fit(df, labels)
        
        # Run a prediction
        prediction = model.predict(df.iloc[0:1])
        
        return jsonify({
            "status": "success",
            "message": "ML Pipeline Operational",
            "dummy_prediction": int(prediction[0]),
            "xgboost_version": xgb.__version__
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# @app.route('/test-openai')
# def test_openai():
#     """Tests OpenAI API connection."""
#     if not openai_client:
#         return jsonify({"status": "skipped", "message": "No API Key found"}), 400
    
#     try:
#         # Minimal API call
#         completion = openai_client.chat.completions.create(
#             model="gpt-4o-mini", # or gpt-3.5-turbo
#             messages=[{"role": "user", "content": "Return the word 'Connected'."}],
#             max_tokens=5
#         )
#         return jsonify({
#             "status": "success",
#             "reply": completion.choices[0].message.content
#         })
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/test-gemini')
def test_gemini():
    """Tests Gemini API connection."""
    if not gemini_client:
        return jsonify({"status": "skipped", "message": "No API Key found"}), 400
    
    try:
        response = gemini_client.generate_content("Say 'Connected' if working")
        return jsonify({
            "status": "success",
            "reply": response.text.strip(),
            "model": "gemini-1.5-flash"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/test-supabase')
def test_supabase():
    """Tests Supabase connection."""
    if not supabase:
        return jsonify({"status": "skipped", "message": "No Supabase Creds found"}), 400
    
    try:
        # Attempt a lightweight auth check or health check
        # (This doesn't require a specific table to exist yet)
        response = supabase.auth.get_session()
        return jsonify({
            "status": "success",
            "message": "Supabase Connection Established", 
            "session_data": "Session object retrieved (normally None if not logged in)"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test-plotly')
def test_plotly():
    """Tests Plotly JSON generation."""
    try:
        fig = go.Figure(data=[go.Bar(y=[1, 3, 2])])
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return jsonify({
            "status": "success", 
            "message": "Plotly JSON generated",
            "data_length": len(graph_json)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("\n🚀 Starting Test Server on http://localhost:5000")
    app.run(debug=True, port=5000)
