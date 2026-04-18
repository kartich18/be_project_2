"""Key lifecycle and rotation analytics routes."""

from flask import Blueprint, jsonify

from app.services.analytics_service import AnalyticsService
from app.utils.logger import logger


keys_bp = Blueprint("keys", __name__)


@keys_bp.route("/v1/keys/rotation-health", methods=["GET"])
def rotation_health():
    """Return key rotation health index and compliance score."""
    try:
        result = AnalyticsService.get_rotation_health()
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rotation health endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@keys_bp.route("/v1/keys/age-distribution", methods=["GET"])
def age_distribution():
    """Return key age histogram used by rotation diagnostics."""
    try:
        result = AnalyticsService.get_key_age_distribution()
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Key age distribution endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
