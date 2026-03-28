from flask import Blueprint, jsonify, request
from app.services.harvest_service import HarvestService
from app.utils.logger import logger

harvest_bp = Blueprint("harvest", __name__)

@harvest_bp.route("/harvest/start", methods=["POST"])
def start_harvest():
    """Trigger Phase 1 of the simulation."""
    data = request.get_json(silent=True) or {}
    pin = data.get("pin", 2)
    try:
        result = HarvestService.run_harvest(pin)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Harvest failed: %s", e)
        return jsonify({"error": str(e)}), 500

@harvest_bp.route("/harvest/decrypt", methods=["POST"])
def decrypt_harvest():
    """Trigger Phase 3 of the simulation."""
    data = request.get_json(silent=True) or {}
    N = data.get("N", 15)
    e = data.get("e", 3)
    ciphertext = data.get("ciphertext", 8)
    
    try:
        result = HarvestService.run_decryption(N, e, ciphertext)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Quantum decryption failed: %s", e)
        return jsonify({"error": str(e)}), 500
