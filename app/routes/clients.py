"""
Client routes — manage registered client nodes.

Replaces ``peer.py`` from the P2P era.  There are no more HMAC-signed
node-to-node endpoints.  All communication from clients to the server
uses JWT-authenticated HTTPS; the server pushes events back via SSE.

Endpoints
---------
GET  /api/clients                  — list all registered clients (JWT)
POST /api/clients/register         — auto-register a client on startup (shared secret)
POST /api/clients/<client_id>/heartbeat — update last_seen (JWT)
DELETE /api/clients/<client_id>    — deregister a client (JWT admin)
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, current_app

from app import db
from app.models.client import Client
from app.utils.auth_helpers import token_required, admin_required
from app.utils.logger import logger

clients_bp = Blueprint("clients", __name__)


# ---------------------------------------------------------------------------
# GET /api/clients
# ---------------------------------------------------------------------------

@clients_bp.route("/clients", methods=["GET"])
@token_required
def list_clients():
    """Return all registered client nodes."""
    clients = db.session.query(Client).order_by(Client.registered_at.desc()).all()
    return jsonify({"clients": [c.to_dict() for c in clients]}), 200


# ---------------------------------------------------------------------------
# POST /api/clients/register
# ---------------------------------------------------------------------------

@clients_bp.route("/clients/register", methods=["POST"])
def register_client():
    """
    Auto-register a client node.

    This endpoint does NOT require a JWT — it is protected by the shared
    ``CLIENT_REGISTRATION_SECRET`` so that new client nodes can bootstrap
    themselves without an admin having to pre-register them.

    Body:
        {
            "client_id":   "C1",
            "port":        5001,
            "secret":      "<CLIENT_REGISTRATION_SECRET>",
            "ip_address":  "192.168.1.10"   (optional — falls back to remote_addr)
        }
    """
    data      = request.get_json(silent=True) or {}
    secret    = (data.get("secret") or "").strip()
    client_id = (data.get("client_id") or "").strip()
    port      = int(data.get("port", 5001))
    ip        = (data.get("ip_address") or request.remote_addr or "127.0.0.1").strip()

    # Validate shared secret
    expected = current_app.config.get("CLIENT_REGISTRATION_SECRET", "")
    if not secret or secret != expected:
        logger.warning("Client registration rejected — bad secret from %s", ip)
        return jsonify({"error": "Invalid registration secret"}), 403

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    # Upsert — if already registered, just refresh last_seen
    client = db.session.query(Client).filter_by(client_id=client_id).first()
    if client:
        client.touch()
        client.port       = port
        client.ip_address = ip
    else:
        client = Client(
            client_id=client_id,
            port=port,
            ip_address=ip,
            last_seen=datetime.now(timezone.utc),
            status="online",
        )
        db.session.add(client)

    db.session.commit()
    logger.info("Client registered: %s at %s:%d", client_id, ip, port)
    return jsonify({"message": "Registered successfully", "client": client.to_dict()}), 200


# ---------------------------------------------------------------------------
# POST /api/clients/<client_id>/heartbeat
# ---------------------------------------------------------------------------

@clients_bp.route("/clients/<client_id>/heartbeat", methods=["POST"])
@token_required
def client_heartbeat(client_id: str):
    """Update last_seen for a connected client."""
    client = db.session.query(Client).filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Unknown client_id"}), 404
    client.touch()
    db.session.commit()
    return jsonify({"ok": True}), 200


# ---------------------------------------------------------------------------
# DELETE /api/clients/<client_id>
# ---------------------------------------------------------------------------

@clients_bp.route("/clients/<client_id>", methods=["DELETE"])
@admin_required
def deregister_client(client_id: str):
    """Deregister (remove) a client node. Admin only."""
    client = db.session.query(Client).filter_by(client_id=client_id).first()
    if not client:
        return jsonify({"error": "Unknown client_id"}), 404
    db.session.delete(client)
    db.session.commit()
    logger.info("Client deregistered: %s", client_id)
    return jsonify({"message": f"Client {client_id} removed"}), 200
