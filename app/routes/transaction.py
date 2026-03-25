"""
Transaction route — POST /api/transaction.

Accepts transaction payload, processes with both classical and PQC methods,
returns timing comparison.
"""
from flask import Blueprint, jsonify, request

from app.services.transaction_service import TransactionService
from app.utils.helpers import validate_transaction_payload
from app.utils.logger import logger

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/transaction", methods=["POST"])
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
        return jsonify({"error": error_msg}), 400

    try:
        result = TransactionService.process_transaction(data)
        return jsonify(result), 201
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transaction processing failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
