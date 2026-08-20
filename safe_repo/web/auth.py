import os
import json
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from flask import request, session, redirect, render_template_string, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash

AUTH_FILE = Path(__file__).resolve().parent.parent / "core" / "mongo" / "users_auth.json"
RESET_TOKENS_FILE = Path(__file__).resolve().parent.parent / "core" / "mongo" / "reset_tokens.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_users() -> Dict[str, Any]:
    data = _read_json(AUTH_FILE, {"users": {}})
    if "users" not in data:
        data["users"] = {}
    return data


def _save_users(data: Dict[str, Any]) -> None:
    _write_json(AUTH_FILE, data)


def _load_reset_tokens() -> Dict[str, Any]:
    return _read_json(RESET_TOKENS_FILE, {"tokens": {}})


def _save_reset_tokens(data: Dict[str, Any]) -> None:
    _write_json(RESET_TOKENS_FILE, data)


def generate_password_hash_func(password: str) -> str:
    return generate_password_hash(password)


def verify_password_hash_func(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def create_user(username: str, email: str, password: str, is_admin: bool = False) -> Optional[Dict[str, Any]]:
    data = _load_users()
    users = data["users"]

    if any(u.get("username") == username for u in users.values()):
        return None
    if any(u.get("email") == email for u in users.values()):
        return None

    user_id = secrets.token_hex(8)
    users[user_id] = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": generate_password_hash_func(password),
        "created_at": datetime.utcnow().isoformat(),
        "is_admin": is_admin,
    }
    _save_users(data)
    return users[user_id]


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    data = _load_users()
    for user in data["users"].values():
        if user.get("username") == username:
            if verify_password_hash_func(user.get("password_hash", ""), password):
                return user
    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    data = _load_users()
    return data["users"].get(user_id)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    data = _load_users()
    for user in data["users"].values():
        if user.get("username") == username:
            return user
    return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    data = _load_users()
    for user in data["users"].values():
        if user.get("email") == email:
            return user
    return None


def update_user_password(user_id: str, new_password: str) -> bool:
    data = _load_users()
    user = data["users"].get(user_id)
    if not user:
        return False
    user["password_hash"] = generate_password_hash_func(new_password)
    _save_users(data)
    return True


def generate_reset_token(email: str) -> Optional[str]:
    user = get_user_by_email(email)
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    token_data = _load_reset_tokens()
    token_data["tokens"][token] = {
        "user_id": user["id"],
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
    }
    _save_reset_tokens(token_data)
    return token


def verify_reset_token(token: str) -> Optional[Dict[str, Any]]:
    token_data = _load_reset_tokens()
    entry = token_data["tokens"].get(token)
    if not entry:
        return None
    expires_at = datetime.fromisoformat(entry["expires_at"])
    if datetime.utcnow() > expires_at:
        del token_data["tokens"][token]
        _save_reset_tokens(token_data)
        return None
    return entry


def consume_reset_token(token: str) -> Optional[str]:
    entry = verify_reset_token(token)
    if not entry:
        return None
    token_data = _load_reset_tokens()
    del token_data["tokens"][token]
    _save_reset_tokens(token_data)
    return entry["user_id"]


def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/auth/login")
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/auth/login")
        user = get_user_by_id(session["user_id"])
        if not user or not user.get("is_admin"):
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def current_user() -> Optional[Dict[str, Any]]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def register_view():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            return render_template_string(REGISTER_TEMPLATE, errors=errors, username=username, email=email)

        user = create_user(username, email, password)
        if not user:
            error = "Username or email already exists."
            return render_template_string(REGISTER_TEMPLATE, errors=[error], username=username, email=email)

        session["user_id"] = user["id"]
        return redirect("/auth/profile")

    return render_template_string(REGISTER_TEMPLATE, errors=[], username="", email="")


def login_view():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        remember = request.form.get("remember") == "on"

        user = authenticate_user(username, password)
        if user:
            session["user_id"] = user["id"]
            session.permanent = True
            if remember:
                app_config = {"remember_me": True}
            else:
                app_config = {}
            return redirect("/auth/profile")
        error = "Invalid username or password."
        return render_template_string(LOGIN_TEMPLATE, error=error, username=username)

    return render_template_string(LOGIN_TEMPLATE, error=None, username="")


def logout_view():
    session.pop("user_id", None)
    session.pop("is_admin", None)
    return redirect("/")


def forgot_password_view():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if not email:
            return render_template_string(FORGOT_PASSWORD_TEMPLATE, error="Email is required.", success=None)
        user = get_user_by_email(email)
        if not user:
            return render_template_string(FORGOT_PASSWORD_TEMPLATE, error="No account found with that email.", success=None)
        token = generate_reset_token(email)
        if not token:
            return render_template_string(FORGOT_PASSWORD_TEMPLATE, error="Unable to generate reset token.", success=None)
        reset_link = request.url_root.rstrip("/") + f"/auth/reset-password/{token}"
        return render_template_string(FORGOT_PASSWORD_TEMPLATE, error=None, success=f"Reset link: {reset_link}")
    return render_template_string(FORGOT_PASSWORD_TEMPLATE, error=None, success=None)


def reset_password_view(token: str):
    user_id = consume_reset_token(token)
    if not user_id:
        return render_template_string(RESET_PASSWORD_TEMPLATE, error="Invalid or expired reset token.", token=token)
    if request.method == "POST":
        password = (request.form.get("password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()
        if not password or len(password) < 6:
            return render_template_string(RESET_PASSWORD_TEMPLATE, error="Password must be at least 6 characters.", token=token)
        if password != confirm_password:
            return render_template_string(RESET_PASSWORD_TEMPLATE, error="Passwords do not match.", token=token)
        update_user_password(user_id, password)
        return redirect("/auth/login")
    return render_template_string(RESET_PASSWORD_TEMPLATE, error=None, token=token)


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login - StudyHub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #f8fafc;
        }
        .login-container {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }
        .login-header {
            text-align: center;
            margin-bottom: 32px;
        }
        .login-header h1 {
            font-size: 28px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .login-header p {
            color: #94a3b8;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            color: #f8fafc;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2563eb;
            background: rgba(30, 41, 59, 0.8);
        }
        .form-group input::placeholder {
            color: #64748b;
        }
        .error-message {
            color: #fca5a5;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: rgba(220, 38, 38, 0.1);
            border-radius: 6px;
            display: none;
        }
        .error-message.show {
            display: block;
        }
        .remember-me {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            font-size: 14px;
            color: #94a3b8;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .links {
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
        }
        .links a {
            color: #93c5fd;
            text-decoration: none;
            margin: 0 8px;
        }
        .links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>👋 Welcome Back</h1>
            <p>Sign in to your StudyHub account</p>
        </div>
        {% if error %}
        <div class="error-message show">⚠️ {{ error }}</div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" value="{{ username }}" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter your password" required>
            </div>
            <div class="remember-me">
                <input type="checkbox" name="remember" id="remember">
                <label for="remember" style="margin:0; cursor:pointer;">Remember me</label>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="links">
            <a href="/auth/register">Create account</a>
            <a href="/auth/forgot-password">Forgot password?</a>
        </div>
    </div>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Register - StudyHub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #f8fafc;
        }
        .register-container {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }
        .register-header {
            text-align: center;
            margin-bottom: 32px;
        }
        .register-header h1 {
            font-size: 28px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .register-header p {
            color: #94a3b8;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            color: #f8fafc;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2563eb;
            background: rgba(30, 41, 59, 0.8);
        }
        .form-group input::placeholder {
            color: #64748b;
        }
        .error-message {
            color: #fca5a5;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: rgba(220, 38, 38, 0.1);
            border-radius: 6px;
            display: none;
        }
        .error-message.show {
            display: block;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .links {
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
            color: #94a3b8;
        }
        .links a {
            color: #93c5fd;
            text-decoration: none;
            margin: 0 8px;
        }
        .links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="register-container">
        <div class="register-header">
            <h1>🚀 Create Account</h1>
            <p>Join StudyHub and start learning</p>
        </div>
        {% if errors %}
        <div class="error-message show">
            <ul style="padding-left:18px;">
                {% for error in errors %}
                <li>{{ error }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" value="{{ username }}" placeholder="Choose a username" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" value="{{ email }}" placeholder="you@example.com" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="At least 6 characters" required>
            </div>
            <div class="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirm_password" placeholder="Repeat your password" required>
            </div>
            <button type="submit">Create Account</button>
        </form>
        <div class="links">
            <span>Already have an account?</span>
            <a href="/auth/login">Sign in</a>
        </div>
    </div>
</body>
</html>
"""

FORGOT_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forgot Password - StudyHub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #f8fafc;
        }
        .forgot-container {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }
        .forgot-header {
            text-align: center;
            margin-bottom: 32px;
        }
        .forgot-header h1 {
            font-size: 28px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .forgot-header p {
            color: #94a3b8;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            color: #f8fafc;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2563eb;
            background: rgba(30, 41, 59, 0.8);
        }
        .error-message {
            color: #fca5a5;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: rgba(220, 38, 38, 0.1);
            border-radius: 6px;
            display: none;
        }
        .error-message.show {
            display: block;
        }
        .success-message {
            color: #86efac;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: rgba(22, 163, 74, 0.1);
            border-radius: 6px;
            display: none;
        }
        .success-message.show {
            display: block;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .links {
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
            color: #94a3b8;
        }
        .links a {
            color: #93c5fd;
            text-decoration: none;
        }
        .links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="forgot-container">
        <div class="forgot-header">
            <h1>🔑 Reset Password</h1>
            <p>Enter your email to receive a reset link</p>
        </div>
        {% if error %}
        <div class="error-message show">⚠️ {{ error }}</div>
        {% endif %}
        {% if success %}
        <div class="success-message show">✅ {{ success }}</div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" placeholder="you@example.com" required>
            </div>
            <button type="submit">Send Reset Link</button>
        </form>
        <div class="links">
            <a href="/auth/login">Back to login</a>
        </div>
    </div>
</body>
</html>
"""

RESET_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Reset Password - StudyHub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #f8fafc;
        }
        .reset-container {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }
        .reset-header {
            text-align: center;
            margin-bottom: 32px;
        }
        .reset-header h1 {
            font-size: 28px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .reset-header p {
            color: #94a3b8;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            color: #f8fafc;
            font-size: 14px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2563eb;
            background: rgba(30, 41, 59, 0.8);
        }
        .error-message {
            color: #fca5a5;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 12px;
            background: rgba(220, 38, 38, 0.1);
            border-radius: 6px;
            display: none;
        }
        .error-message.show {
            display: block;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .links {
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
            color: #94a3b8;
        }
        .links a {
            color: #93c5fd;
            text-decoration: none;
        }
        .links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="reset-container">
        <div class="reset-header">
            <h1>🔐 New Password</h1>
            <p>Choose a new password for your account</p>
        </div>
        {% if error %}
        <div class="error-message show">⚠️ {{ error }}</div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label>New Password</label>
                <input type="password" name="password" placeholder="At least 6 characters" required>
            </div>
            <div class="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirm_password" placeholder="Repeat new password" required>
            </div>
            <button type="submit">Update Password</button>
        </form>
        <div class="links">
            <a href="/auth/login">Back to login</a>
        </div>
    </div>
</body>
</html>
"""
