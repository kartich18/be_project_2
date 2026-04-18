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
from app.utils.logger import logger
from app.models.transaction import Transaction
from app.models.user import User
from flask_jwt_extended import get_jwt_identity
from app import db

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/transaction", methods=["POST"])
@token_required
def create_transaction():
    """Process a banking transaction through both crypto pipelines.

    Expects JSON: ``{"amount": float, "account_id_from": str, "account_id_to": str}``

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
            sender=(data or {}).get("account_id_from") if isinstance(data, dict) else None,
            receiver=(data or {}).get("account_id_to") if isinstance(data, dict) else None,
            error_message=error_msg,
        )
        return jsonify({"error": error_msg}), 400

    try:
        origin_ip = request.remote_addr
        result = TransactionService.process_transaction(data, origin_ip=origin_ip)
        return jsonify(result), 201
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transaction processing failed: %s", exc)
        if isinstance(data, dict):
            AnalyticsService.log_security_event(
                event_type="internal_error",
                algorithm=None,
                sender=data.get("account_id_from"),
                receiver=data.get("account_id_to"),
                error_message=str(exc),
            )
        return jsonify({"error": "Internal server error"}), 500

@transaction_bp.route("/transactions/history", methods=["GET"])
@token_required
def get_transaction_history():
    """Returns past transactions solely involving the authenticated user."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "Invalid user"}), 401
    
    # We allow filtering by limiting rows or returning all
    limit = request.args.get("limit", 100, type=int)

    if user.role == "admin":
        transactions = db.session.query(Transaction).order_by(Transaction.timestamp.desc()).limit(limit).all()
        return jsonify({"transactions": [tx.to_dict() for tx in transactions]}), 200

    from app.models.account import Account
    accounts = db.session.query(Account).filter_by(user_id=user.id).all()
    account_ids = [a.account_number for a in accounts]
    
    if not account_ids:
        return jsonify({"transactions": []}), 200
        
    transactions = db.session.query(Transaction).filter(
        db.or_(
            Transaction.sender.in_(account_ids),
            Transaction.receiver.in_(account_ids)
        )
    ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    return jsonify({"transactions": [tx.to_dict() for tx in transactions]}), 200
