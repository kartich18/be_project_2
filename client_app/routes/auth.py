"""
client_app/routes/auth.py — login/logout for the client node.

The client app does NOT maintain its own user database.
It proxies credentials to the central server's POST /api/auth/login,
stores the returned JWT in client_state.state, and uses it for all
subsequent requests to the server.
"""
import requests as http

from flask import (
    Blueprint, render_template, request, redirect, url_for, jsonify, current_app
)

from client_app.client_state import state

client_auth_bp = Blueprint("client_auth", __name__)


# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------

@client_auth_bp.route("/login", methods=["GET"])
def login_page():
    """Render the login form."""
    if state.is_authenticated():
        return redirect(url_for("client_tx.dashboard"))
    return render_template("login.html",
                           client_id=state.client_id or current_app.config["CLIENT_ID"])


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@client_auth_bp.route("/login", methods=["POST"])
def login():
    """
    Proxy login to the central server.
    On success stores JWT in state and redirects to dashboard.
    """
    data     = request.get_json(silent=True) or request.form.to_dict()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    server_url = current_app.config["SERVER_URL"]
    try:
        resp = http.post(
            f"{server_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
            verify=False,   # self-signed cert — skip TLS verification
        )
    except Exception as exc:
        return jsonify({"error": f"Cannot reach server: {exc}"}), 503

    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        return jsonify({"error": body.get("error", "Login failed")}), resp.status_code

    body = resp.json()
    state.jwt_token = body["access_token"]
    state.username  = body.get("user", {}).get("username", username)

    # If form POST (non-AJAX), redirect to dashboard
    if request.content_type and "application/json" in request.content_type:
        return jsonify({"ok": True, "username": state.username}), 200
    return redirect(url_for("client_tx.dashboard"))


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@client_auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear in-memory JWT and redirect to login."""
    state.clear()
    return redirect(url_for("client_auth.login_page"))
