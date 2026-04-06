"""
Transaction route — POST /api/transaction.

Accepts transaction payload, processes with both classical and PQC methods,
returns timing comparison.
"""
from flask import Blueprint, jsonify, request

from app.services.analytics_service import AnalyticsService
from app.services.transaction_service import TransactionService
from app.utils.auth_helpers import token_required
from app.utils.helpers import validate_transaction_payload
from app.utils.hmac_auth import require_hmac_signature
from app.utils.logger import logger

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/transaction", methods=["POST"])
@token_required
def create_transaction():
    """Process a banking transaction through both crypto pipelines.

    Expects JSON: ``{"amount": float, "sender": str, "receiver": str}``

    Returns:
        201 — comparison dict with classical and pqc results.
        400 — validation error.
        500 — internal processing error.
    """
    logger.debug("Received transaction payload from client")
    data = request.get_json(silent=True)
    logger.debug("Payload contents: %s", data)

    is_valid, error_msg = validate_transaction_payload(data)
    if not is_valid:
        AnalyticsService.log_security_event(
            event_type="validation_error",
            algorithm=None,
            sender=(data or {}).get("sender") if isinstance(data, dict) else None,
            receiver=(data or {}).get("receiver") if isinstance(data, dict) else None,
            error_message=error_msg,
        )
        return jsonify({"error": error_msg}), 400

    try:
        origin_ip = request.remote_addr
        result = TransactionService.process_transaction(data, origin_ip=origin_ip, broadcast=True)
        return jsonify(result), 201
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transaction processing failed: %s", exc)
        if isinstance(data, dict):
            AnalyticsService.log_security_event(
                event_type="internal_error",
                algorithm=None,
                sender=data.get("sender"),
                receiver=data.get("receiver"),
                error_message=str(exc),
            )
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# P2P receive endpoint (HMAC-protected, NOT JWT-protected)
# ---------------------------------------------------------------------------

@transaction_bp.route("/p2p/transaction", methods=["POST"])
@require_hmac_signature
def receive_p2p_transaction():
    """
    Receive a transaction broadcast from a peer node.
    Processes and stores it locally. Does NOT re-broadcast (broadcast=False)
    to avoid infinite loops.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No payload"}), 400

    is_valid, error_msg = validate_transaction_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    try:
        origin_ip = request.remote_addr
        result = TransactionService.process_transaction(
            data,
            origin_ip=origin_ip,
            broadcast=False,  # don't re-broadcast to avoid infinite loops
        )
        logger.info("Received P2P transaction from %s", origin_ip)
        return jsonify(result), 201
    except Exception as exc:
        logger.exception("P2P transaction processing failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
