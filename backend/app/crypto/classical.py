"""
Classical cryptography module — RSA-2048.

Provides key generation, encryption (OAEP), decryption,
signing (PSS), and verification using the `cryptography` library.
All operations return timing data for benchmarking.
"""

import time
from typing import Union

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Key Generation
# ---------------------------------------------------------------------------

def generate_keypair(key_size: int = 2048):
    """
    Generate an RSA key pair.

    Args:
        key_size: RSA key size in bits (default 2048).

    Returns:
        dict with keys: private_key, public_key, elapsed_ms,
        public_key_bytes, private_key_bytes.
    """
    start = time.perf_counter_ns()

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    public_key = private_key.public_key()

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    # Serialised sizes for comparison metrics
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    logger.debug(
        "RSA-%d keygen in %.3f ms  (pub %d B, priv %d B)",
        key_size, elapsed_ms, len(pub_bytes), len(priv_bytes),
    )

    return {
        "private_key": private_key,
        "public_key": public_key,
        "elapsed_ms": elapsed_ms,
        "public_key_bytes": len(pub_bytes),
        "private_key_bytes": len(priv_bytes),
    }


# ---------------------------------------------------------------------------
# Encrypt / Decrypt  (RSA-OAEP, SHA-256)
# ---------------------------------------------------------------------------

def encrypt(public_key, plaintext: bytes) -> dict:
    """
    Encrypt plaintext with RSA-OAEP.

    Args:
        public_key: RSA public key object.
        plaintext:  Data to encrypt (must be ≤ 190 bytes for RSA-2048/SHA-256).

    Returns:
        dict with keys: ciphertext, elapsed_ms, ciphertext_bytes.
    """
    start = time.perf_counter_ns()

    ciphertext = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    logger.debug("RSA-OAEP encrypt in %.3f ms (%d B)", elapsed_ms, len(ciphertext))

    return {
        "ciphertext": ciphertext,
        "elapsed_ms": elapsed_ms,
        "ciphertext_bytes": len(ciphertext),
    }


def decrypt(private_key, ciphertext: bytes) -> dict:
    """
    Decrypt ciphertext with RSA-OAEP.

    Args:
        private_key: RSA private key object.
        ciphertext:  Data to decrypt.

    Returns:
        dict with keys: plaintext, elapsed_ms.
    """
    start = time.perf_counter_ns()

    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    logger.debug("RSA-OAEP decrypt in %.3f ms", elapsed_ms)

    return {
        "plaintext": plaintext,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Sign / Verify  (RSA-PSS, SHA-256)
# ---------------------------------------------------------------------------

def sign(private_key, message: bytes) -> dict:
    """
    Sign a message with RSA-PSS.

    Args:
        private_key: RSA private key object.
        message:     Data to sign.

    Returns:
        dict with keys: signature, elapsed_ms.
    """
    start = time.perf_counter_ns()

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    logger.debug("RSA-PSS sign in %.3f ms", elapsed_ms)

    return {
        "signature": signature,
        "elapsed_ms": elapsed_ms,
    }


def verify(public_key, message: bytes, signature: bytes) -> dict:
    """
    Verify an RSA-PSS signature.

    Args:
        public_key: RSA public key object.
        message:    Original message bytes.
        signature:  Signature bytes to verify.

    Returns:
        dict with keys: is_valid (bool), elapsed_ms.
    """
    start = time.perf_counter_ns()

    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        is_valid = True
    except InvalidSignature:
        is_valid = False

    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    logger.debug("RSA-PSS verify in %.3f ms — valid=%s", elapsed_ms, is_valid)

    return {
        "is_valid": is_valid,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# End-to-end helper
# ---------------------------------------------------------------------------

def encrypt_transaction(plaintext: Union[bytes, str]) -> dict:
    """
    Run a full RSA-2048 encrypt → decrypt cycle and return all timing data.

    This is the function consumed by the benchmark and transaction-service layers.

    Args:
        plaintext: Transaction payload (str will be UTF-8 encoded).

    Returns:
        dict with keys:
            method, key_gen_ms, encrypt_ms, decrypt_ms, total_ms,
            public_key_bytes, private_key_bytes, ciphertext_bytes,
            verified (bool).
    """
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    # 1. Key generation
    keygen = generate_keypair()

    # 2. Encrypt
    enc = encrypt(keygen["public_key"], plaintext)

    # 3. Decrypt
    dec = decrypt(keygen["private_key"], enc["ciphertext"])

    # 4. Sign + verify (integrity check)
    sig = sign(keygen["private_key"], plaintext)
    ver = verify(keygen["public_key"], plaintext, sig["signature"])

    total_ms = keygen["elapsed_ms"] + enc["elapsed_ms"] + dec["elapsed_ms"]

    return {
        "method": "RSA-2048",
        "key_gen_ms": round(keygen["elapsed_ms"], 4),
        "encrypt_ms": round(enc["elapsed_ms"], 4),
        "decrypt_ms": round(dec["elapsed_ms"], 4),
        "sign_ms": round(sig["elapsed_ms"], 4),
        "verify_ms": round(ver["elapsed_ms"], 4),
        "total_ms": round(total_ms, 4),
        "public_key_bytes": keygen["public_key_bytes"],
        "private_key_bytes": keygen["private_key_bytes"],
        "ciphertext_bytes": enc["ciphertext_bytes"],
        "verified": ver["is_valid"],
    }
