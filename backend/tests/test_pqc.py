"""
Tests for the post-quantum ML-KEM-768 + AES-256-GCM module.

All tests are SKIPPED if liboqs is not installed.
"""

import pytest

from app.crypto import pqc

# Skip the entire module if PQC is not available
pytestmark = pytest.mark.skipif(
    not pqc.PQC_AVAILABLE,
    reason="liboqs not installed — skipping PQC tests",
)

SAMPLE_PLAINTEXT = b"Hello, quantum-safe banking!"


class TestPQCAvailable:
    """Verify liboqs availability flag."""

    def test_pqc_available(self):
        assert pqc.PQC_AVAILABLE is True


class TestKEM:
    """ML-KEM-768 key encapsulation tests."""

    def test_keygen(self):
        result = pqc.generate_keypair()
        assert "public_key" in result
        assert "kem" in result
        assert result["elapsed_ms"] > 0
        assert result["public_key_bytes"] > 0

    def test_encapsulate_decapsulate_roundtrip(self):
        keygen = pqc.generate_keypair()
        encap = pqc.encapsulate(keygen["public_key"])
        decap = pqc.decapsulate(keygen["kem"], encap["ciphertext"])
        assert encap["shared_secret"] == decap["shared_secret"]

    def test_different_keypairs_different_secrets(self):
        kg1 = pqc.generate_keypair()
        kg2 = pqc.generate_keypair()
        enc1 = pqc.encapsulate(kg1["public_key"])
        enc2 = pqc.encapsulate(kg2["public_key"])
        # Shared secrets should differ (with overwhelming probability)
        assert enc1["shared_secret"] != enc2["shared_secret"]


class TestAESGCM:
    """AES-256-GCM encryption tests using a synthetic key."""

    def test_round_trip(self):
        key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
        enc = pqc.aes_gcm_encrypt(key, SAMPLE_PLAINTEXT)
        dec = pqc.aes_gcm_decrypt(key, enc["encrypted_data"])
        assert dec["plaintext"] == SAMPLE_PLAINTEXT

    def test_tampered_ciphertext_fails(self):
        key = b"0123456789abcdef0123456789abcdef"
        enc = pqc.aes_gcm_encrypt(key, SAMPLE_PLAINTEXT)
        tampered = enc["encrypted_data"][:-1] + bytes([enc["encrypted_data"][-1] ^ 0xFF])
        with pytest.raises(Exception):
            pqc.aes_gcm_decrypt(key, tampered)

    def test_wrong_key_fails(self):
        key1 = b"0123456789abcdef0123456789abcdef"
        key2 = b"abcdef0123456789abcdef0123456789"
        enc = pqc.aes_gcm_encrypt(key1, SAMPLE_PLAINTEXT)
        with pytest.raises(Exception):
            pqc.aes_gcm_decrypt(key2, enc["encrypted_data"])


class TestEncryptTransaction:
    """End-to-end ML-KEM-768 + AES-GCM transaction tests."""

    def test_returns_expected_structure(self):
        result = pqc.encrypt_transaction(SAMPLE_PLAINTEXT)
        expected_keys = {
            "method", "key_gen_ms", "encapsulate_ms", "encrypt_ms",
            "decapsulate_ms", "decrypt_ms", "total_ms",
            "public_key_bytes", "secret_key_bytes",
            "ciphertext_bytes", "verified",
        }
        assert expected_keys.issubset(result.keys())

    def test_method_label(self):
        result = pqc.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["method"] == "ML-KEM-768"

    def test_verified_flag(self):
        result = pqc.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["verified"] is True

    def test_accepts_string(self):
        result = pqc.encrypt_transaction("string payload")
        assert result["verified"] is True

    def test_timings_positive(self):
        result = pqc.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["key_gen_ms"] > 0
        assert result["total_ms"] > 0
