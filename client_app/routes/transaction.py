"""
client_app/routes/transaction.py — dashboard and transaction submission.

- GET  /        — client dashboard (own transactions only)
- POST /transaction — forward tx intent to server, return result to browser
"""
import requests as http

from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, current_app
)

from client_app.client_state import state
from client_app.services.sync_service import SyncService

client_tx_bp = Blueprint("client_tx", __name__)


def _require_auth():
    """Return a redirect if not authenticated, else None."""
    if not state.is_authenticated():
        return redirect(url_for("client_auth.login_page"))
    return None


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@client_tx_bp.route("/")
def dashboard():
    """Render the per-client dashboard."""
    guard = _require_auth()
    if guard:
        return guard
    client_id = current_app.config["CLIENT_ID"]
    txs = SyncService.get_local_transactions(limit=50)
    return render_template(
        "dashboard.html",
        client_id=client_id,
        username=state.username,
        transactions=txs,
        server_url=current_app.config["SERVER_URL"],
    )


# ---------------------------------------------------------------------------
# POST /transaction
# ---------------------------------------------------------------------------

@client_tx_bp.route("/transaction", methods=["POST"])
def submit_transaction():
    """
    Forward a transaction intent to the central server.

    Body (JSON): { "receiver": "C2", "amount": 500, "currency": "INR" }

    The sender is implicitly this client's CLIENT_ID.
    Returns the server's comparison response (classical + pqc results).
    """
    guard = _require_auth()
    if guard:
        return jsonify({"error": "Not authenticated"}), 401

    data      = request.get_json(silent=True) or {}
    client_id = current_app.config["CLIENT_ID"]

    payload = {
        "sender":   client_id,
        "receiver": data.get("receiver", ""),
        "amount":   float(data.get("amount", 0)),
        "currency": data.get("currency", "INR"),
    }

    server_url = current_app.config["SERVER_URL"]
    try:
        resp = http.post(
            f"{server_url}/api/transaction",
            json=payload,
            headers=state.auth_headers(),
            timeout=15,
            verify=False,   # self-signed cert — skip TLS verification
        )
    except Exception as exc:
        return jsonify({"error": f"Cannot reach server: {exc}"}), 503

    body = resp.json() if resp.content else {}

    if resp.status_code == 201:
        # Also save the sent transaction to local DB
        SyncService.save_transaction(body, direction="sent")
        return jsonify(body), 201

    return jsonify(body), resp.status_code


# ---------------------------------------------------------------------------
# GET /transactions  (REST — returns JSON list for AJAX polling)
# ---------------------------------------------------------------------------

@client_tx_bp.route("/transactions", methods=["GET"])
def list_transactions():
    """Return local transaction history as JSON."""
    guard = _require_auth()
    if guard:
        return jsonify({"error": "Not authenticated"}), 401
    txs = SyncService.get_local_transactions(limit=100)
    return jsonify({"transactions": txs}), 200
