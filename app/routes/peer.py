"""
Peer routes — P2P node registration and health endpoints.

All /api/p2p/* routes are authenticated with HMAC signatures (not JWT).
They are exempt from the JWT before_request guard.

Dashboard (JWT) endpoints:
    GET  /api/peers              — list known peers (JWT protected)
    POST /api/peers/connect      — tell this node to connect to a new peer (JWT protected)

P2P (HMAC) endpoints:
    POST /api/p2p/peers/register — peer-to-peer registration announcement
    POST /api/p2p/peers/ping     — heartbeat from a peer
"""
import json

from flask import Blueprint, jsonify, request

from app.services.peer_service import PeerService
from app.utils.auth_helpers import token_required
from app.utils.hmac_auth import require_hmac_signature
from app.utils.logger import logger

peer_bp = Blueprint("peer", __name__)


# ---------------------------------------------------------------------------
# Dashboard-facing (JWT-protected)
# ---------------------------------------------------------------------------

@peer_bp.route("/peers", methods=["GET"])
@token_required
def list_peers():
    """Return all known peers."""
    peers = PeerService.get_active_peers()
    return jsonify({"peers": [p.to_dict() for p in peers]}), 200


@peer_bp.route("/peers/connect", methods=["POST"])
@token_required
def connect_to_peer():
    """
    Instruct this node to connect to a remote peer.

    Body: { "ip_address": str, "port": int }

    This node will:
    1. Announce itself to the remote peer.
    2. Register the remote peer locally.
    """
    data = request.get_json(silent=True) or {}
    ip   = (data.get("ip_address") or "").strip()
    port = int(data.get("port", 5000))

    if not ip:
        return jsonify({"error": "ip_address is required"}), 400

    # Build the remote node URL and announce
    scheme = "https"
    peer_url = f"{scheme}://{ip}:{port}"

    success = PeerService.announce_to_peer(peer_url)

    if success:
        # Register them locally so we know to broadcast to them
        peer = PeerService.register_peer(ip_address=ip, port=port)
        return jsonify({"message": "Connected to peer", "peer": peer.to_dict()}), 200
    else:
        return jsonify({"error": "Failed to reach peer — check IP, port, and PEER_HMAC_SECRET"}), 502


# ---------------------------------------------------------------------------
# P2P-facing (HMAC-protected) — exempt from JWT guard
# ---------------------------------------------------------------------------

@peer_bp.route("/p2p/peers/register", methods=["POST"])
@require_hmac_signature
def p2p_register():
    """
    Receive a peer registration announcement from another node.
    The remote node is telling us about itself.
    """
    data = request.get_json(silent=True) or {}
    ip   = (data.get("ip_address") or request.remote_addr or "").strip()
    port = int(data.get("port", 5000))
    host = data.get("hostname", ip)

    peer = PeerService.register_peer(ip_address=ip, port=port, hostname=host)
    logger.info("Received peer registration from %s:%d", ip, port)

    # Return our own identity so the peer can record us too
    from flask import current_app
    import socket
    return jsonify({
        "message": "Registered successfully",
        "peer":    peer.to_dict(),
        "self": {
            "ip_address": current_app.config.get("NODE_IP", "127.0.0.1"),
            "port":       current_app.config.get("NODE_PORT", 5000),
            "hostname":   socket.gethostname(),
        },
    }), 200


@peer_bp.route("/p2p/peers/ping", methods=["POST"])
@require_hmac_signature
def p2p_ping():
    """
    Heartbeat endpoint — update last_seen for the calling peer.
    """
    ip   = request.remote_addr
    port = request.get_json(silent=True, force=True) or {}
    port = int(port.get("port", 5000)) if isinstance(port, dict) else 5000

    # Touch the peer if we know about them
    from app import db
    from app.models.peer import Peer
    peer = db.session.query(Peer).filter_by(ip_address=ip, port=port).first()
    if peer:
        peer.touch()
        db.session.commit()

    return jsonify({"pong": True}), 200
