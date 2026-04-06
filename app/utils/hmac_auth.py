"""
HMAC-SHA256 authentication for P2P node-to-node requests.

Both nodes must share the same PEER_HMAC_SECRET (set in .env).

Outbound requests: call sign_p2p_request() to add signature headers.
Inbound requests:  decorate with @require_hmac_signature to verify.

Header protocol:
    X-Node-Timestamp : ISO-8601 UTC timestamp (used for replay protection)
    X-Node-Signature : HMAC-SHA256(secret, method+path+timestamp+body_hex)
"""
import hashlib
import hmac
import time
from datetime import datetime, timezone
from functools import wraps

from flask import current_app, jsonify, request


# Maximum age of a signed request in seconds (replay protection)
_MAX_AGE_SECONDS = 30


def _compute_signature(secret: str, method: str, path: str, timestamp: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature for a request."""
    body_hex = body.hex() if body else ""
    message = f"{method.upper()}|{path}|{timestamp}|{body_hex}"
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def sign_p2p_request(method: str, path: str, body: bytes = b"") -> dict:
    """
    Generate HMAC signature headers for an outbound P2P request.

    Returns a dict of headers to merge into the outbound request.
    """
    secret    = current_app.config.get("PEER_HMAC_SECRET", "")
    timestamp = datetime.now(timezone.utc).isoformat()
    sig       = _compute_signature(secret, method, path, timestamp, body)
    return {
        "X-Node-Timestamp": timestamp,
        "X-Node-Signature": sig,
    }


def require_hmac_signature(fn):
    """
    Decorator that verifies the HMAC signature on incoming P2P requests.

    Returns 401 if the signature is missing, expired, or invalid.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        timestamp = request.headers.get("X-Node-Timestamp", "")
        signature = request.headers.get("X-Node-Signature", "")

        if not timestamp or not signature:
            return jsonify({"error": "Missing P2P authentication headers"}), 401

        # Replay protection — reject requests older than _MAX_AGE_SECONDS
        try:
            ts = datetime.fromisoformat(timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if abs(age) > _MAX_AGE_SECONDS:
                return jsonify({"error": "P2P request timestamp expired"}), 401
        except ValueError:
            return jsonify({"error": "Invalid timestamp format"}), 401

        # Recompute and compare
        secret   = current_app.config.get("PEER_HMAC_SECRET", "")
        body     = request.get_data()
        expected = _compute_signature(secret, request.method, request.path, timestamp, body)

        if not hmac.compare_digest(expected, signature):
            return jsonify({"error": "Invalid P2P signature"}), 401

        return fn(*args, **kwargs)
    return wrapper
