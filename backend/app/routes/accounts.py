from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.account import Account
from app.models.user import User
import uuid

accounts_bp = Blueprint("accounts", __name__)

@accounts_bp.route("/accounts", methods=["GET"])
@jwt_required()
def get_accounts():
    """List all accounts for the authenticated user."""
    user_id = int(get_jwt_identity())
    accounts = Account.query.filter_by(user_id=user_id).all()
    return jsonify({"accounts": [a.to_dict() for a in accounts]}), 200

@accounts_bp.route("/accounts", methods=["POST"])
@jwt_required()
def create_account():
    """Create a new account for the user."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    currency = data.get("currency", "INR")
    
    new_account = Account(
        user_id=user_id,
        account_number=uuid.uuid4().hex[:16].upper(),
        balance=0.0,
        currency=currency
    )
    db.session.add(new_account)
    db.session.commit()
    
    return jsonify({
        "message": "Account created successfully", 
        "account": new_account.to_dict()
    }), 201

@accounts_bp.route("/directory/users", methods=["GET"])
@jwt_required()
def get_directory():
    """List all users and their primary accounts (safely for transfers)."""
    users = db.session.query(User, Account).join(Account, User.id == Account.user_id).all()
    # Filter to 1 primary account per user
    results = {}
    for user, acct in users:
        if user.username not in results:
            results[user.username] = {
                "username": user.username,
                "account_id": acct.account_number
            }
    return jsonify({"users": list(results.values())}), 200

