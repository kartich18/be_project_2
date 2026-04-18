from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from app.services.harvest_service import HarvestService
from app.utils.auth_helpers import token_required
from app.utils.logger import logger

harvest_bp = Blueprint("harvest", __name__)


@harvest_bp.route("/harvest/start", methods=["POST"])
@harvest_bp.route("/harvest/encrypt", methods=["POST"])
@token_required
def start_harvest():
    """Trigger Phase 1 of the simulation (encrypt a PIN with RSA-15)."""
    data = request.get_json(silent=True) or {}
    # Accept 'pin' (legacy) or 'message' (new React frontend)
    pin = data.get("message", data.get("pin", 2))
    user_id = get_jwt_identity()
    try:
        result = HarvestService.run_harvest(pin, user_id=user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Harvest failed: %s", e)
        return jsonify({"error": str(e)}), 500


@harvest_bp.route("/harvest/decrypt", methods=["POST"])
@token_required
def decrypt_harvest():
    """Trigger Phase 3 of the simulation (quantum Shor's attack)."""
    data = request.get_json(silent=True) or {}
    # Accept both 'N' (legacy) and 'n' (React frontend)
    N         = data.get("n", data.get("N", 15))
    e         = data.get("e", 3)
    ciphertext = data.get("ciphertext", 8)

    try:
        result = HarvestService.run_decryption(N, e, ciphertext)
        return jsonify(result), 200
    except Exception as exc:
        logger.exception("Quantum decryption failed: %s", exc)
        return jsonify({"error": str(exc)}), 500
