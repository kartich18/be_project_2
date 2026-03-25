"""
Metrics route — GET /api/metrics, GET /api/benchmark.

Returns aggregated benchmark data and on-demand comparison results.
"""
from flask import Blueprint

metrics_bp = Blueprint("metrics", __name__)


# Endpoints will be implemented in Phase 4
