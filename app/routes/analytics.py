"""Advanced analytics routes for dashboard enhancement."""

from flask import Blueprint, jsonify, request

from app.services.analytics_service import AnalyticsService
from app.utils.logger import logger


analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/v1/analytics/latency-percentiles", methods=["GET"])
def latency_percentiles():
    """Return p50/p95/p99 latency percentiles and trend."""
    algorithm = request.args.get("algorithm", default=None, type=str)
    time_window = request.args.get("time_window", default="24h", type=str)

    try:
        result = AnalyticsService.get_latency_percentiles(
            algorithm=algorithm,
            time_window=time_window,
        )
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Latency percentile endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/migration-status", methods=["GET"])
def migration_status():
    """Return ML-KEM migration progress and trend."""
    time_window = request.args.get("time_window", default="24h", type=str)

    try:
        result = AnalyticsService.get_migration_status(time_window=time_window)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Migration status endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/algorithm-comparison", methods=["GET"])
def algorithm_comparison():
    """Return comparative performance ratio between RSA and ML-KEM."""
    time_window = request.args.get("time_window", default="24h", type=str)

    try:
        result = AnalyticsService.get_algorithm_comparison(time_window=time_window)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Algorithm comparison endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/security-health", methods=["GET"])
def security_health():
    """Return failure/rejection rates and overall security status."""
    time_window = request.args.get("time_window", default="24h", type=str)
    algorithm = request.args.get("algorithm", default=None, type=str)

    try:
        result = AnalyticsService.get_security_health(
            time_window=time_window,
            algorithm=algorithm,
        )
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Security health endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/anomalies", methods=["GET"])
def anomalies():
    """Return unresolved anomalies with severity metadata."""
    try:
        result = AnalyticsService.get_anomalies()
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Anomalies endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
