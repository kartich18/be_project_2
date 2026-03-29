"""
Benchmark module — comparative timing analysis.

Runs N iterations of keygen, encrypt, decrypt for both classical (RSA-2048)
and post-quantum (ML-KEM-512 / ML-KEM-768 / ML-KEM-1024) methods.
Returns structured comparison data.
"""

import statistics

from app.crypto import classical
from app.crypto import pqc as pqc_mod
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_stats(values: list[float]) -> dict:
    """Return min / max / avg / median / stdev for a list of float values."""
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "median": 0, "stdev": 0}

    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "avg": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "stdev": round(statistics.stdev(values) if len(values) > 1 else 0, 4),
    }


SAMPLE_PAYLOAD = b'{"amount":1000,"sender":"Alice","receiver":"Bob"}'


# ---------------------------------------------------------------------------
# Classical benchmark
# ---------------------------------------------------------------------------

def run_classical_benchmark(iterations: int = 100, payload: bytes = SAMPLE_PAYLOAD) -> dict:
    """
    Run *iterations* RSA-2048 encrypt_transaction cycles.

    Returns:
        dict with per-operation stats and key/ciphertext sizes.
    """
    logger.info("Starting RSA-2048 benchmark — %d iterations", iterations)

    key_gen_times = []
    encrypt_times = []
    decrypt_times = []
    total_times = []
    sign_times = []
    verify_times = []

    key_sizes = {}

    for i in range(iterations):
        result = classical.encrypt_transaction(payload)
        key_gen_times.append(result["key_gen_ms"])
        encrypt_times.append(result["encrypt_ms"])
        decrypt_times.append(result["decrypt_ms"])
        sign_times.append(result["sign_ms"])
        verify_times.append(result["verify_ms"])
        total_times.append(result["total_ms"])

        if i == 0:
            key_sizes = {
                "public_key_bytes": result["public_key_bytes"],
                "private_key_bytes": result["private_key_bytes"],
                "ciphertext_bytes": result["ciphertext_bytes"],
            }

    logger.info(
        "RSA-2048 benchmark complete — avg total %.3f ms",
        statistics.mean(total_times),
    )

    return {
        "method": "RSA-2048",
        "iterations": iterations,
        "key_gen": _compute_stats(key_gen_times),
        "encrypt": _compute_stats(encrypt_times),
        "decrypt": _compute_stats(decrypt_times),
        "sign": _compute_stats(sign_times),
        "verify": _compute_stats(verify_times),
        "total": _compute_stats(total_times),
        "key_sizes": key_sizes,
    }


# ---------------------------------------------------------------------------
# PQC benchmark
# ---------------------------------------------------------------------------

def run_pqc_benchmark(
    iterations: int = 100,
    payload: bytes = SAMPLE_PAYLOAD,
    algorithm: str = "ML-KEM-768",
) -> dict:
    """
    Run *iterations* ML-KEM + AES-256-GCM encrypt_transaction cycles.

    Args:
        iterations: Number of benchmark iterations.
        payload:    Sample transaction payload.
        algorithm:  KEM algorithm name (ML-KEM-512, ML-KEM-768, ML-KEM-1024).

    Raises RuntimeError if liboqs is not installed.

    Returns:
        dict with per-operation stats and key/ciphertext sizes.
    """
    if not pqc_mod.PQC_AVAILABLE:
        raise RuntimeError(
            "Cannot run PQC benchmark — liboqs is not installed."
        )

    logger.info("Starting %s benchmark — %d iterations", algorithm, iterations)

    key_gen_times = []
    encapsulate_times = []
    encrypt_times = []
    decapsulate_times = []
    decrypt_times = []
    total_times = []

    key_sizes = {}

    for i in range(iterations):
        result = pqc_mod.encrypt_transaction(payload, algorithm=algorithm)
        key_gen_times.append(result["key_gen_ms"])
        encapsulate_times.append(result["encapsulate_ms"])
        encrypt_times.append(result["encrypt_ms"])
        decapsulate_times.append(result["decapsulate_ms"])
        decrypt_times.append(result["decrypt_ms"])
        total_times.append(result["total_ms"])

        if i == 0:
            key_sizes = {
                "public_key_bytes": result["public_key_bytes"],
                "secret_key_bytes": result["secret_key_bytes"],
                "ciphertext_bytes": result["ciphertext_bytes"],
            }

    logger.info(
        "%s benchmark complete — avg total %.3f ms",
        algorithm,
        statistics.mean(total_times),
    )

    return {
        "method": algorithm,
        "iterations": iterations,
        "key_gen": _compute_stats(key_gen_times),
        "encapsulate": _compute_stats(encapsulate_times),
        "encrypt": _compute_stats(encrypt_times),
        "decapsulate": _compute_stats(decapsulate_times),
        "decrypt": _compute_stats(decrypt_times),
        "total": _compute_stats(total_times),
        "key_sizes": key_sizes,
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def run_comparison(iterations: int = 100, payload: bytes = SAMPLE_PAYLOAD) -> dict:
    """
    Run both classical and PQC benchmarks and return a unified comparison.

    If liboqs is unavailable, the PQC sections will contain error messages
    instead of benchmark data.

    Returns:
        dict with keys: iterations, classical, pqc_512, pqc_768, pqc_1024, key_sizes.
    """
    logger.info("Running comparison benchmark — %d iterations", iterations)

    classical_result = run_classical_benchmark(iterations, payload)

    pqc_results = {}
    if pqc_mod.PQC_AVAILABLE:
        for algo in pqc_mod.KEM_ALGORITHMS:
            pqc_results[algo] = run_pqc_benchmark(iterations, payload, algorithm=algo)
    else:
        for algo in pqc_mod.KEM_ALGORITHMS:
            pqc_results[algo] = {
                "method": algo,
                "error": "liboqs not installed — PQC benchmark skipped",
            }

    comparison = {
        "iterations": iterations,
        "classical": classical_result,
        "pqc_512": pqc_results.get("ML-KEM-512"),
        "pqc_768": pqc_results.get("ML-KEM-768"),
        "pqc_1024": pqc_results.get("ML-KEM-1024"),
        "key_sizes": {
            "classical": classical_result.get("key_sizes", {}),
            "pqc_512": pqc_results.get("ML-KEM-512", {}).get("key_sizes", {}),
            "pqc_768": pqc_results.get("ML-KEM-768", {}).get("key_sizes", {}),
            "pqc_1024": pqc_results.get("ML-KEM-1024", {}).get("key_sizes", {}),
        },
    }

    logger.info("Comparison benchmark complete")
    return comparison
