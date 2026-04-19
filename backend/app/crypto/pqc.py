"""
Post-quantum cryptography module — ML-KEM-512 / ML-KEM-768 / ML-KEM-1024
                                 + ML-DSA-44  / ML-DSA-65  / ML-DSA-87.

Implements:
  • Key encapsulation/decapsulation (ML-KEM) via liboqs (FIPS 203)
  • Digital signatures (ML-DSA) via liboqs (FIPS 204)
  • AES-256-GCM symmetric encryption for the actual payload

Security-level pairings (Option B — matched NIST levels):
  ML-KEM-512  ↔ ML-DSA-44   (Level 2)
  ML-KEM-768  ↔ ML-DSA-65   (Level 3)
  ML-KEM-1024 ↔ ML-DSA-87   (Level 5)

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
    logger.info("liboqs loaded — PQC operations available (ML-KEM + ML-DSA)")
except (ImportError, OSError, SystemExit):
    logger.warning(
        "liboqs-python not available. PQC operations will be disabled. "
        "Build and install liboqs, then `pip install liboqs-python`."
    )

# ---------------------------------------------------------------------------
# KEM configuration
# ---------------------------------------------------------------------------

KEM_ALGORITHM  = "ML-KEM-768"                                    # default
KEM_ALGORITHMS = ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]    # all levels

# ---------------------------------------------------------------------------
# DSA configuration (FIPS 204 — ML-DSA / Dilithium)
# Option B: paired security levels
# ---------------------------------------------------------------------------

DSA_ALGORITHM  = "ML-DSA-65"    # default (Level 3)
DSA_ALGORITHMS = ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"]

# Paired KEM → DSA at matching NIST security level
KEM_TO_DSA: dict[str, str] = {
    "ML-KEM-512":  "ML-DSA-44",   # Level 2
    "ML-KEM-768":  "ML-DSA-65",   # Level 3
    "ML-KEM-1024": "ML-DSA-87",   # Level 5
}

# ---------------------------------------------------------------------------
# AES-GCM constants
# ---------------------------------------------------------------------------

AES_KEY_BITS  = 256
AES_KEY_BYTES = AES_KEY_BITS // 8
NONCE_BYTES   = 12  # 96-bit nonce for AES-GCM


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
# DSA  (ML-DSA via liboqs — FIPS 204)
# ---------------------------------------------------------------------------

def generate_dsa_keypair(algorithm: str = DSA_ALGORITHM) -> dict:
    """
    Generate an ML-DSA signing key pair.

    Args:
        algorithm: DSA algorithm name ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87").
                   Defaults to ML-DSA-65 (Level 3).

    Returns:
        dict with keys: sig (the Signature object, holds secret key),
        public_key (bytes), elapsed_ms, public_key_bytes, secret_key_bytes.
    """
    _require_pqc()
    start = time.perf_counter_ns()

    sig = _oqs.Signature(algorithm)
    public_key = sig.generate_keypair()

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "%s DSA keygen in %.3f ms  (pub %d B, secret %d B)",
        algorithm, elapsed_ms, len(public_key), sig.length_secret_key,
    )

    return {
        "sig": sig,
        "public_key": public_key,
        "elapsed_ms": elapsed_ms,
        "public_key_bytes": len(public_key),
        "secret_key_bytes": sig.length_secret_key,
    }


def sign_dsa(sig_obj, message: bytes) -> dict:
    """
    Sign a message with ML-DSA.

    Args:
        sig_obj: The Signature object from generate_dsa_keypair() that holds
                 the secret key.
        message: Data to sign (the original plaintext payload).

    Returns:
        dict with keys: signature (bytes), elapsed_ms, signature_bytes.
    """
    _require_pqc()
    start = time.perf_counter_ns()

    signature = sig_obj.sign(message)

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "ML-DSA sign in %.3f ms  (sig %d B)",
        elapsed_ms, len(signature),
    )

    return {
        "signature": signature,
        "elapsed_ms": elapsed_ms,
        "signature_bytes": len(signature),
    }


def verify_dsa(public_key: bytes, message: bytes, signature: bytes,
               algorithm: str = DSA_ALGORITHM) -> dict:
    """
    Verify an ML-DSA signature.

    Args:
        public_key: DSA public key bytes from generate_dsa_keypair().
        message:    Original message that was signed.
        signature:  Signature bytes from sign_dsa().
        algorithm:  DSA algorithm name (must match the signing algorithm).

    Returns:
        dict with keys: is_valid (bool), elapsed_ms.
    """
    _require_pqc()
    start = time.perf_counter_ns()

    verifier = _oqs.Signature(algorithm)
    is_valid = verifier.verify(message, signature, public_key)

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    logger.debug(
        "ML-DSA verify in %.3f ms — valid=%s",
        elapsed_ms, is_valid,
    )

    return {
        "is_valid": bool(is_valid),
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# End-to-end helper  (KEM + AES-GCM + ML-DSA)
# ---------------------------------------------------------------------------

def encrypt_transaction(plaintext: Union[bytes, str], algorithm: str = KEM_ALGORITHM) -> dict:
    """
    Run a full ML-KEM + AES-256-GCM + ML-DSA sign/verify cycle.

    The DSA algorithm is automatically selected to match the KEM security
    level (Option B — paired NIST levels):
        ML-KEM-512  → ML-DSA-44  (Level 2)
        ML-KEM-768  → ML-DSA-65  (Level 3)
        ML-KEM-1024 → ML-DSA-87  (Level 5)

    Workflow:
        1.  KEM keygen
        2.  KEM encapsulate  → shared secret
        3.  AES-GCM encrypt payload with shared secret
        4.  DSA keygen
        5.  ML-DSA sign(plaintext)
        6.  KEM decapsulate  → recover shared secret
        7.  AES-GCM decrypt  → recover payload
        8.  ML-DSA verify(signature)
        9.  verified = (plaintext match) AND (dsa.is_valid)

    Args:
        plaintext: Transaction payload (str will be UTF-8 encoded).
        algorithm: KEM algorithm name (default "ML-KEM-768").

    Returns:
        dict with keys:
            method, key_gen_ms, encapsulate_ms, encrypt_ms,
            decapsulate_ms, decrypt_ms,
            dsa_algorithm, dsa_keygen_ms, sign_ms, verify_ms,
            public_key_bytes, secret_key_bytes, ciphertext_bytes,
            dsa_public_key_bytes, signature_bytes,
            verified (bool), dsa_verified (bool).
    """
    _require_pqc()

    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    dsa_algorithm = KEM_TO_DSA.get(algorithm, DSA_ALGORITHM)

    # 1. KEM key generation
    keygen = generate_keypair(algorithm)

    # 2. Encapsulate (sender side)
    encap = encapsulate(keygen["public_key"], algorithm)

    # 3. AES-GCM encrypt with shared secret
    enc = aes_gcm_encrypt(encap["shared_secret"], plaintext)

    # 4. DSA key generation
    dsa_kp = generate_dsa_keypair(dsa_algorithm)

    # 5. ML-DSA sign the original plaintext
    sig_result = sign_dsa(dsa_kp["sig"], plaintext)

    # 6. Decapsulate (receiver side)
    decap = decapsulate(keygen["kem"], encap["ciphertext"])

    # 7. AES-GCM decrypt with recovered shared secret
    dec = aes_gcm_decrypt(decap["shared_secret"], enc["encrypted_data"])

    # 8. ML-DSA verify
    ver = verify_dsa(dsa_kp["public_key"], dec["plaintext"],
                     sig_result["signature"], dsa_algorithm)

    # 9. Combined integrity check
    plaintext_match = dec["plaintext"] == plaintext
    verified = plaintext_match and ver["is_valid"]

    total_ms = (
        keygen["elapsed_ms"]
        + encap["elapsed_ms"]
        + enc["elapsed_ms"]
        + dsa_kp["elapsed_ms"]
        + sig_result["elapsed_ms"]
        + decap["elapsed_ms"]
        + dec["elapsed_ms"]
        + ver["elapsed_ms"]
    )

    return {
        # KEM fields
        "method":            algorithm,
        "key_gen_ms":        round(keygen["elapsed_ms"], 4),
        "encapsulate_ms":    round(encap["elapsed_ms"], 4),
        "encrypt_ms":        round(enc["elapsed_ms"], 4),
        "decapsulate_ms":    round(decap["elapsed_ms"], 4),
        "decrypt_ms":        round(dec["elapsed_ms"], 4),
        "public_key_bytes":  keygen["public_key_bytes"],
        "secret_key_bytes":  keygen["secret_key_bytes"],
        "ciphertext_bytes":  len(enc["encrypted_data"]),
        # DSA fields
        "dsa_algorithm":         dsa_algorithm,
        "dsa_keygen_ms":         round(dsa_kp["elapsed_ms"], 4),
        "sign_ms":               round(sig_result["elapsed_ms"], 4),
        "verify_ms":             round(ver["elapsed_ms"], 4),
        "dsa_public_key_bytes":  dsa_kp["public_key_bytes"],
        "signature_bytes":       sig_result["signature_bytes"],
        "dsa_verified":          ver["is_valid"],
        # Combined
        "total_ms":  round(total_ms, 4),
        "verified":  verified,
    }


def encrypt_transaction_all(plaintext: Union[bytes, str]) -> dict:
    """
    Run encrypt_transaction for every supported ML-KEM security level.
    Each KEM level uses its paired ML-DSA algorithm (Option B).

    Args:
        plaintext: Transaction payload.

    Returns:
        dict keyed by algorithm name, e.g.:
        {
            "ML-KEM-512":  { ..., "dsa_algorithm": "ML-DSA-44", ... },
            "ML-KEM-768":  { ..., "dsa_algorithm": "ML-DSA-65", ... },
            "ML-KEM-1024": { ..., "dsa_algorithm": "ML-DSA-87", ... },
        }
    """
    results = {}
    for algo in KEM_ALGORITHMS:
        results[algo] = encrypt_transaction(plaintext, algorithm=algo)
    return results
