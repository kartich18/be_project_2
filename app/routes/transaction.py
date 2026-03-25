"""
Transaction route — POST /api/transaction.

Accepts transaction payload, processes with both classical and PQC methods,
returns timing comparison.
"""
from flask import Blueprint

transaction_bp = Blueprint("transaction", __name__)


# Endpoints will be implemented in Phase 4
