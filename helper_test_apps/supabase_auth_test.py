import os
from flask import Flask, request, session, redirect, url_for, render_template_string
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY (or SUPABASE_KEY) in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Supabase Auth Test</title>
  <style>
    body { font-family: system-ui, Arial; max-width: 780px; margin: 40px auto; padding: 0 16px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin: 16px 0; }
    input { width: 100%; padding: 10px; margin: 6px 0 12px; }
    button { padding: 10px 14px; cursor: pointer; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .msg { padding: 10px; border-radius: 10px; background: #f5f5f5; }
    .ok { background: #e7ffef; border: 1px solid #b7f7c8; }
    .err { background: #ffeaea; border: 1px solid #ffbdbd; }
    a { text-decoration: none; }
  </style>
</head>
<body>
  <h1>Supabase Auth Test (Email/Password)</h1>

  {% if message %}
    <div class="msg {{ 'ok' if ok else 'err' }}">{{ message }}</div>
  {% endif %}

  <div class="card">
    <h2>Status</h2>
    {% if user %}
      <p><b>Logged in as:</b> {{ user.get('email') }}</p>
      <p><b>User ID:</b> {{ user.get('id') }}</p>
      <p><b>Access token present:</b> {{ 'yes' if session.get('sb_access_token') else 'no' }}</p>
      <form method="POST" action="/logout">
        <button type="submit">Logout</button>
      </form>
    {% else %}
      <p>Not logged in.</p>
    {% endif %}
  </div>

  <div class="row">
    <div class="card">
      <h2>Signup</h2>
      <form method="POST" action="/signup">
        <label>Email</label>
        <input name="email" type="email" required placeholder="you@example.com" />
        <label>Password</label>
        <input name="password" type="password" required minlength="6" placeholder="min 6 chars" />
        <button type="submit">Create account</button>
      </form>
      <p style="color:#666; font-size: 14px;">
        Note: If email confirmations are enabled in Supabase, signup may require email verification before login.
      </p>
    </div>

    <div class="card">
      <h2>Login</h2>
      <form method="POST" action="/login">
        <label>Email</label>
        <input name="email" type="email" required placeholder="you@example.com" />
        <label>Password</label>
        <input name="password" type="password" required placeholder="••••••••" />
        <button type="submit">Login</button>
      </form>
    </div>
  </div>

  <div class="card">
    <h2>Debug</h2>
    <p><a href="/me">GET /me</a> (uses stored access token to fetch current user)</p>
  </div>
</body>
</html>
"""

def _get_current_user_from_token():
    """Fetch current user using stored access token (server-side)."""
    token = session.get("sb_access_token")
    if not token:
        return None
    try:
        res = supabase.auth.get_user(token)
        return res.user.model_dump() if res and res.user else None
    except Exception:
        return None


@app.get("/")
def home():
    user = _get_current_user_from_token()
    return render_template_string(PAGE, user=user, message=None, ok=True)


@app.post("/signup")
def signup():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    try:
        res = supabase.auth.sign_up({"email": email, "password": password})

        # Supabase may return a session OR require email confirmation (session None)
        if res.session:
            session["sb_access_token"] = res.session.access_token
            session["sb_refresh_token"] = res.session.refresh_token
            session["sb_user_email"] = res.user.email if res.user else email
            return render_template_string(PAGE, user=_get_current_user_from_token(),
                                          message="✅ Signup successful and logged in.", ok=True)

        return render_template_string(PAGE, user=None,
                                      message="✅ Signup created. Check email to confirm (if enabled), then login.",
                                      ok=True)
    except Exception as e:
        return render_template_string(PAGE, user=None, message=f"❌ Signup failed: {e}", ok=False), 400


@app.post("/login")
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})

        # Save tokens into Flask session so we can call supabase.auth.get_user(token)
        session["sb_access_token"] = res.session.access_token
        session["sb_refresh_token"] = res.session.refresh_token
        session["sb_user_email"] = res.user.email if res.user else email

        return redirect(url_for("home"))
    except Exception as e:
        return render_template_string(PAGE, user=None, message=f"❌ Login failed: {e}", ok=False), 401


@app.post("/logout")
def logout():
    # Optional: attempt Supabase sign-out (not strictly required for server session)
    try:
        token = session.get("sb_access_token")
        if token:
            # supabase-py uses client state; for a clean test, we just clear cookies/server session.
            pass
    except Exception:
        pass

    session.clear()
    return redirect(url_for("home"))


@app.get("/me")
def me():
    user = _get_current_user_from_token()
    if not user:
        return {"logged_in": False}, 401
    return {"logged_in": True, "user": user}


if __name__ == "__main__":
    # Use one host consistently to avoid cookie/session confusion
    app.run(host="127.0.0.1", port=5001, debug=True)
