"""
Metrics route — GET /api/metrics, GET /api/benchmark.

Returns aggregated benchmark data and on-demand comparison results.
"""
from flask import Blueprint, current_app, jsonify, request

from app.crypto.benchmark import run_comparison
from app.services.transaction_service import TransactionService
from app.utils.logger import logger

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def get_metrics():
    """Return aggregated performance metrics from recent transactions.

    Query params:
        method  — ``RSA-2048``, ``ML-KEM-512``, ``ML-KEM-768``,
                  or ``ML-KEM-1024`` (optional, default: all)
        last    — max rows to consider (optional, default: 100)

    Returns:
        200 — metrics dict with classical and/or pqc_512/pqc_768/pqc_1024 sub-dicts.
        500 — internal error.
    """
    method = request.args.get("method", default=None, type=str)
    limit = request.args.get("last", default=100, type=int)
    logger.debug("Received metrics request. method=%s, last=%s", method, limit)

    # Clamp limit to a sane range
    limit = max(1, min(limit, 10000))

    try:
        result = TransactionService.get_metrics(method=method, limit=limit)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Metrics retrieval failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@metrics_bp.route("/benchmark", methods=["GET"])
def run_benchmark():
    """Run an on-demand benchmark comparing classical vs PQC.

    Query params:
        iterations — number of iterations (optional, default from config,
                     capped at BENCHMARK_MAX_ITERATIONS).

    Returns:
        200 — full comparison dict.
        400 — invalid iterations parameter.
        500 — internal error.
    """
    default_iter = current_app.config.get("BENCHMARK_DEFAULT_ITERATIONS", 100)
    max_iter = current_app.config.get("BENCHMARK_MAX_ITERATIONS", 10000)

    iterations_str = request.args.get("iterations", default=None)
    logger.debug("Received benchmark request. iterations_str=%s", iterations_str)

    if iterations_str is not None:
        try:
            iterations = int(iterations_str)
        except (ValueError, TypeError):
            return jsonify({"error": "iterations must be a positive integer"}), 400
        if iterations <= 0:
            return jsonify({"error": "iterations must be a positive integer"}), 400
    else:
        iterations = default_iter

    # Cap at max
    iterations = min(iterations, max_iter)

    try:
        result = run_comparison(iterations)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Benchmark failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
