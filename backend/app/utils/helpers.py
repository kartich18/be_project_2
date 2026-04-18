"""
Helper utilities — common functions used across the application.
"""
import time
import uuid
from functools import wraps


def generate_transaction_id() -> str:
    """Generate a unique transaction ID."""
    return str(uuid.uuid4())


def timer(func):
    """
    Decorator that measures execution time of a function.

    Returns a tuple of (result, elapsed_time_ms).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter_ns()
        result = func(*args, **kwargs)
        elapsed_ns = time.perf_counter_ns() - start
        elapsed_ms = elapsed_ns / 1_000_000  # Convert to milliseconds
        return result, elapsed_ms
    return wrapper


def ns_to_ms(nanoseconds: int) -> float:
    """Convert nanoseconds to milliseconds."""
    return nanoseconds / 1_000_000


def format_bytes(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def validate_transaction_payload(data: dict) -> tuple[bool, str]:
    """
    Validate incoming transaction request payload.

    Args:
        data: Request JSON data.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not data:
        return False, "Request body is required"

    required_fields = ["amount", "account_id_from", "account_id_to"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'"

    # Validate amount
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return False, "Amount must be a positive number"
    except (ValueError, TypeError):
        return False, "Amount must be a valid number"

    # Validate sender and receiver
    if not isinstance(data["account_id_from"], str) or not data["account_id_from"].strip():
        return False, "Sender must be a non-empty string"
    if not isinstance(data["account_id_to"], str) or not data["account_id_to"].strip():
        return False, "Receiver must be a non-empty string"
    if data["account_id_from"].strip() == data["account_id_to"].strip():
        return False, "Sender and receiver must be different"

    return True, ""
