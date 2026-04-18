"""
Tests for the classical RSA-2048 cryptography module.
"""

import pytest
from app.crypto import classical


SAMPLE_PLAINTEXT = b"Hello, quantum-safe banking!"


class TestKeyGeneration:
    """RSA key generation tests."""

    def test_keygen_returns_expected_keys(self):
        result = classical.generate_keypair()
        assert "private_key" in result
        assert "public_key" in result
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] > 0

    def test_keygen_key_sizes(self):
        result = classical.generate_keypair()
        # RSA-2048 DER-encoded key sizes
        assert result["public_key_bytes"] > 200  # ~294 B typical
        assert result["private_key_bytes"] > 1000  # ~1218 B typical
        assert result["private_key_bytes"] > result["public_key_bytes"]


class TestEncryptDecrypt:
    """RSA-OAEP encrypt/decrypt round-trip tests."""

    def test_round_trip(self):
        keys = classical.generate_keypair()
        enc = classical.encrypt(keys["public_key"], SAMPLE_PLAINTEXT)
        dec = classical.decrypt(keys["private_key"], enc["ciphertext"])
        assert dec["plaintext"] == SAMPLE_PLAINTEXT

    def test_ciphertext_size(self):
        keys = classical.generate_keypair()
        enc = classical.encrypt(keys["public_key"], SAMPLE_PLAINTEXT)
        # RSA-2048 ciphertext is always 256 bytes
        assert enc["ciphertext_bytes"] == 256

    def test_timing_data_present(self):
        keys = classical.generate_keypair()
        enc = classical.encrypt(keys["public_key"], SAMPLE_PLAINTEXT)
        dec = classical.decrypt(keys["private_key"], enc["ciphertext"])
        assert enc["elapsed_ms"] >= 0
        assert dec["elapsed_ms"] >= 0

    def test_wrong_key_fails(self):
        keys1 = classical.generate_keypair()
        keys2 = classical.generate_keypair()
        enc = classical.encrypt(keys1["public_key"], SAMPLE_PLAINTEXT)
        with pytest.raises(Exception):
            classical.decrypt(keys2["private_key"], enc["ciphertext"])


class TestSignVerify:
    """RSA-PSS sign/verify tests."""

    def test_sign_verify_valid(self):
        keys = classical.generate_keypair()
        sig = classical.sign(keys["private_key"], SAMPLE_PLAINTEXT)
        ver = classical.verify(keys["public_key"], SAMPLE_PLAINTEXT, sig["signature"])
        assert ver["is_valid"] is True

    def test_verify_wrong_message(self):
        keys = classical.generate_keypair()
        sig = classical.sign(keys["private_key"], SAMPLE_PLAINTEXT)
        ver = classical.verify(keys["public_key"], b"tampered message", sig["signature"])
        assert ver["is_valid"] is False

    def test_verify_wrong_key(self):
        keys1 = classical.generate_keypair()
        keys2 = classical.generate_keypair()
        sig = classical.sign(keys1["private_key"], SAMPLE_PLAINTEXT)
        ver = classical.verify(keys2["public_key"], SAMPLE_PLAINTEXT, sig["signature"])
        assert ver["is_valid"] is False


class TestEncryptTransaction:
    """End-to-end encrypt_transaction tests."""

    def test_returns_expected_structure(self):
        result = classical.encrypt_transaction(SAMPLE_PLAINTEXT)
        expected_keys = {
            "method", "key_gen_ms", "encrypt_ms", "decrypt_ms",
            "sign_ms", "verify_ms", "total_ms",
            "public_key_bytes", "private_key_bytes",
            "ciphertext_bytes", "verified",
        }
        assert expected_keys.issubset(result.keys())

    def test_method_label(self):
        result = classical.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["method"] == "RSA-2048"

    def test_verified_flag(self):
        result = classical.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["verified"] is True

    def test_accepts_string(self):
        result = classical.encrypt_transaction("string payload")
        assert result["verified"] is True

    def test_timings_positive(self):
        result = classical.encrypt_transaction(SAMPLE_PLAINTEXT)
        assert result["key_gen_ms"] > 0
        assert result["total_ms"] > 0
