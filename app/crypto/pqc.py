"""
Post-quantum cryptography module — ML-KEM-512 / ML-KEM-768 / ML-KEM-1024.

Implements key encapsulation/decapsulation using liboqs (FIPS 203),
with AES-256-GCM symmetric encryption for the actual payload.
All operations return timing data for benchmarking.

If liboqs is not installed, the module loads without error but all
PQC functions raise RuntimeError. Check ``PQC_AVAILABLE`` at runtime.
"""

import os
import time
from typing import Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Graceful liboqs import
# ---------------------------------------------------------------------------
PQC_AVAILABLE = False
_oqs = None

try:
    import oqs as _oqs  # type: ignore[import-untyped]
    PQC_AVAILABLE = True
    logger.info("liboqs loaded — PQC operations available (ML-KEM-512/768/1024)")
except (ImportError, OSError, SystemExit):
    logger.warning(
        "liboqs-python not available. PQC operations will be disabled. "
        "Build and install liboqs, then `pip install liboqs-python`."
    )

# Default algorithm (backward compatible)
KEM_ALGORITHM = "ML-KEM-768"

# All supported KEM security levels
KEM_ALGORITHMS = ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]

AES_KEY_BITS = 256
AES_KEY_BYTES = AES_KEY_BITS // 8
NONCE_BYTES = 12  # 96-bit nonce for AES-GCM


def _require_pqc():
    """Raise if liboqs is not available."""
    if not PQC_AVAILABLE:
        raise RuntimeError(
            "PQC operations require liboqs. Install the liboqs C library "
            "and `pip install liboqs-python`."
        )


# ---------------------------------------------------------------------------
# Key Derivation  (shared secret → AES-256 key)
# ---------------------------------------------------------------------------

def _derive_aes_key(shared_secret: bytes) -> bytes:
    """Derive a 256-bit AES key from a KEM shared secret using HKDF-SHA256."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=AES_KEY_BYTES,
        salt=None,
        info=b"quantum-safe-banking-aes-key",
    ).derive(shared_secret)


# ---------------------------------------------------------------------------
# KEM  (ML-KEM via liboqs)
# ---------------------------------------------------------------------------

def generate_keypair(algorithm: str = KEM_ALGORITHM):
    """
    Generate an ML-KEM key pair.

    Args:
        algorithm: KEM algorithm name (e.g. "ML-KEM-512", "ML-KEM-768",
                   "ML-KEM-1024"). Defaults to ML-KEM-768.

    Returns:
        dict with keys: secret_key, public_key, elapsed_ms,
        public_key_bytes, secret_key_bytes, kem (the KEM object, needed
        for decapsulation).
    """
    _require_pqc()
    start = time.perf_counter_ns()

    kem = _oqs.KeyEncapsulation(algorithm)
    public_key = kem.generate_keypair()

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "%s keygen in %.3f ms  (pub %d B, secret %d B)",
        algorithm, elapsed_ms, len(public_key), kem.length_secret_key,
    )

    return {
        "kem": kem,
        "public_key": public_key,
        "elapsed_ms": elapsed_ms,
        "public_key_bytes": len(public_key),
        "secret_key_bytes": kem.length_secret_key,
    }


def encapsulate(public_key: bytes, algorithm: str = KEM_ALGORITHM):
    """
    Encapsulate: generate a shared secret for the given public key.

    Args:
        public_key: ML-KEM public key bytes.
        algorithm:  KEM algorithm name. Defaults to ML-KEM-768.

    Returns:
        dict with keys: ciphertext, shared_secret, elapsed_ms.
    """
    _require_pqc()
    start = time.perf_counter_ns()

    kem = _oqs.KeyEncapsulation(algorithm)
    ciphertext, shared_secret = kem.encap_secret(public_key)

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "%s encapsulate in %.3f ms  (ct %d B)",
        algorithm, elapsed_ms, len(ciphertext),
    )

    return {
        "ciphertext": ciphertext,
        "shared_secret": shared_secret,
        "elapsed_ms": elapsed_ms,
    }


def decapsulate(kem, ciphertext: bytes):
    """
    Decapsulate: recover the shared secret.

    Args:
        kem:        The KEM object that holds the secret key (from generate_keypair).
        ciphertext: KEM ciphertext from encapsulate().

    Returns:
        dict with keys: shared_secret, elapsed_ms.
    """
    _require_pqc()
    start = time.perf_counter_ns()

    shared_secret = kem.decap_secret(ciphertext)

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug("KEM decapsulate in %.3f ms", elapsed_ms)

    return {
        "shared_secret": shared_secret,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Symmetric encryption  (AES-256-GCM)
# ---------------------------------------------------------------------------

def aes_gcm_encrypt(key: bytes, plaintext: bytes) -> dict:
    """
    Encrypt with AES-256-GCM.

    The key is first derived through HKDF to ensure it is exactly 256 bits.

    Args:
        key:       Raw key material (e.g. KEM shared secret).
        plaintext: Data to encrypt.

    Returns:
        dict with keys: encrypted_data (nonce ‖ ciphertext ‖ tag), elapsed_ms.
    """
    start = time.perf_counter_ns()

    aes_key = _derive_aes_key(key)
    nonce = os.urandom(NONCE_BYTES)
    aesgcm = AESGCM(aes_key)
    ct = aesgcm.encrypt(nonce, plaintext, None)  # ct includes 16-byte tag

    encrypted_data = nonce + ct  # 12 B nonce ‖ ciphertext ‖ 16 B tag

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "AES-256-GCM encrypt in %.3f ms  (%d B → %d B)",
        elapsed_ms, len(plaintext), len(encrypted_data),
    )

    return {
        "encrypted_data": encrypted_data,
        "elapsed_ms": elapsed_ms,
    }


def aes_gcm_decrypt(key: bytes, encrypted_data: bytes) -> dict:
    """
    Decrypt AES-256-GCM ciphertext.

    Args:
        key:            Raw key material (same as used for encryption).
        encrypted_data: nonce ‖ ciphertext ‖ tag.

    Returns:
        dict with keys: plaintext, elapsed_ms.
    """
    start = time.perf_counter_ns()

    aes_key = _derive_aes_key(key)
    nonce = encrypted_data[:NONCE_BYTES]
    ct = encrypted_data[NONCE_BYTES:]
    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ct, None)

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug("AES-256-GCM decrypt in %.3f ms", elapsed_ms)

    return {
        "plaintext": plaintext,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# End-to-end helper
# ---------------------------------------------------------------------------

def encrypt_transaction(plaintext: Union[bytes, str], algorithm: str = KEM_ALGORITHM) -> dict:
    """
    Run a full ML-KEM + AES-256-GCM encrypt → decrypt cycle.

    Workflow:
        1. KEM keygen
        2. KEM encapsulate  → shared secret
        3. AES-GCM encrypt payload with shared secret
        4. KEM decapsulate  → recover shared secret
        5. AES-GCM decrypt  → recover payload

    Args:
        plaintext: Transaction payload (str will be UTF-8 encoded).
        algorithm: KEM algorithm name (default "ML-KEM-768").

    Returns:
        dict with keys:
            method, key_gen_ms, encapsulate_ms, encrypt_ms,
            decapsulate_ms, decrypt_ms, total_ms,
            public_key_bytes, secret_key_bytes, ciphertext_bytes,
            verified (bool).
    """
    _require_pqc()

    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    # 1. Key generation
    keygen = generate_keypair(algorithm)

    # 2. Encapsulate (sender side)
    encap = encapsulate(keygen["public_key"], algorithm)

    # 3. AES-GCM encrypt with shared secret
    enc = aes_gcm_encrypt(encap["shared_secret"], plaintext)

    # 4. Decapsulate (receiver side)
    decap = decapsulate(keygen["kem"], encap["ciphertext"])

    # 5. AES-GCM decrypt with recovered shared secret
    dec = aes_gcm_decrypt(decap["shared_secret"], enc["encrypted_data"])

    # Verify round-trip integrity
    verified = dec["plaintext"] == plaintext

    total_ms = (
        keygen["elapsed_ms"]
        + encap["elapsed_ms"]
        + enc["elapsed_ms"]
        + decap["elapsed_ms"]
        + dec["elapsed_ms"]
    )

    return {
        "method": algorithm,
        "key_gen_ms": round(keygen["elapsed_ms"], 4),
        "encapsulate_ms": round(encap["elapsed_ms"], 4),
        "encrypt_ms": round(enc["elapsed_ms"], 4),
        "decapsulate_ms": round(decap["elapsed_ms"], 4),
        "decrypt_ms": round(dec["elapsed_ms"], 4),
        "total_ms": round(total_ms, 4),
        "public_key_bytes": keygen["public_key_bytes"],
        "secret_key_bytes": keygen["secret_key_bytes"],
        "ciphertext_bytes": len(enc["encrypted_data"]),
        "verified": verified,
    }


def encrypt_transaction_all(plaintext: Union[bytes, str]) -> dict:
    """
    Run encrypt_transaction for every supported ML-KEM security level.

    Args:
        plaintext: Transaction payload.

    Returns:
        dict keyed by algorithm name, e.g.:
        {
            "ML-KEM-512": { ... },
            "ML-KEM-768": { ... },
            "ML-KEM-1024": { ... },
        }
    """
    results = {}
    for algo in KEM_ALGORITHMS:
        results[algo] = encrypt_transaction(plaintext, algorithm=algo)
    return results
