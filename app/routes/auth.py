"""
Auth routes — user registration, login, refresh, logout, and me.

Endpoints:
    POST /api/auth/register  — Create a new user account
    POST /api/auth/login     — Authenticate and get JWT tokens
    POST /api/auth/refresh   — Exchange refresh token for new access token
    POST /api/auth/logout    — Client-side logout (token blacklisting is stateless here)
    GET  /api/auth/me        — Return current authenticated user info
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request, create_access_token

from app import db
from app.models.user import User
from app.utils.auth_helpers import generate_tokens, token_required
from app.utils.logger import logger

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """
    Register a new user.

    Body: { "username": str, "password": str, "email": str (optional), "role": "admin"|"viewer" }

    Rules:
        - The very first user registered automatically becomes an admin.
        - After the first user exists, only an authenticated admin can create more users.
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email    = (data.get("email") or "").strip() or None
    role     = data.get("role", "viewer")

    # --- Validate inputs ---------------------------------------------------
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if role not in ("admin", "viewer"):
        return jsonify({"error": "role must be 'admin' or 'viewer'"}), 400

    existing_count = db.session.query(User).count()

    # After first user exists, require admin JWT
    if existing_count > 0:
        try:
            verify_jwt_in_request()
            from flask_jwt_extended import get_jwt
            claims = get_jwt()
            if claims.get("role") != "admin":
                return jsonify({"error": "Only admins can create new users"}), 403
        except Exception:
            return jsonify({"error": "Authentication required to create additional users"}), 401

    # --- Check duplicates --------------------------------------------------
    if db.session.query(User).filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409
    if email and db.session.query(User).filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # --- Create user -------------------------------------------------------
    # First ever user is always admin regardless of requested role
    effective_role = "admin" if existing_count == 0 else role

    user = User(username=username, email=email, role=effective_role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    logger.info("New user registered: %s (role=%s)", username, effective_role)
    return jsonify({
        "message": "User created successfully",
        "user": user.to_dict(),
    }), 201


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Authenticate a user.

    Body: { "username": str, "password": str }
    Returns: { "access_token": str, "refresh_token": str, "user": {...} }
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = db.session.query(User).filter_by(username=username).first()

    if not user or not user.check_password(password):
        logger.warning("Failed login attempt for username: %s", username)
        return jsonify({"error": "Invalid username or password"}), 401

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    tokens = generate_tokens(user.id)
    logger.info("User logged in: %s", username)

    return jsonify({
        **tokens,
        "user": user.to_dict(),
    }), 200


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/refresh", methods=["POST"])
def refresh():
    """
    Exchange a valid refresh token for a new access token.
    Send refresh token as Bearer in the Authorization header.
    """
    try:
        verify_jwt_in_request(refresh=True)
        user_id = get_jwt_identity()
    except Exception as exc:
        return jsonify({"error": "Invalid or expired refresh token", "detail": str(exc)}), 401

    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "User no longer exists"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )
    return jsonify({"access_token": access_token}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/logout", methods=["POST"])
@token_required
def logout():
    """
    Logout endpoint. Since we use stateless JWTs, logout is handled
    client-side by deleting the token from localStorage.
    This endpoint exists for auditability / future token blacklisting.
    """
    user_id = get_jwt_identity()
    logger.info("User logged out: id=%s", user_id)
    return jsonify({"message": "Logged out successfully"}), 200


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/me", methods=["GET"])
@token_required
def me():
    """Return the currently authenticated user's profile."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200
