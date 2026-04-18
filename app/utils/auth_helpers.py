from __future__ import annotations
"""
JWT authentication helpers — decorators and token utilities.
"""
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------

def generate_tokens(user_id: int) -> dict:
    """Create an access + refresh token pair for a user."""
    access  = create_access_token(identity=str(user_id))
    refresh = create_refresh_token(identity=str(user_id))
    return {"access_token": access, "refresh_token": refresh}


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def token_required(fn):
    """Require a valid JWT access token. Returns 401 on failure."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return jsonify({"error": "Authentication required", "detail": str(exc)}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    """Require a valid JWT AND admin role. Returns 403 for non-admins."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return jsonify({"error": "Authentication required", "detail": str(exc)}), 401

        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin privileges required"}), 403

        return fn(*args, **kwargs)
    return wrapper


from typing import Optional

def get_current_user_id() -> Optional[int]:
    """Return the current user's ID from the JWT, or None."""
    try:
        verify_jwt_in_request()
        return int(get_jwt_identity())
    except Exception:
        return None
