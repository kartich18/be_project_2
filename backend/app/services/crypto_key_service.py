import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

try:
    import oqs
    _OQS_AVAILABLE = True
except (ImportError, OSError):
    oqs = None  # type: ignore[assignment]
    _OQS_AVAILABLE = False

from app import db
from app.models.user_keys import UserKeys

class CryptoKeyService:
    @staticmethod
    def _derive_kek(password: str, salt: bytes) -> bytes:
        """Derive 256-bit Key Encryption Key (KEK) using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def _encrypt_private_key(private_key_bytes: bytes, password: str) -> dict:
        """Encrypt a private key using AES-256-GCM."""
        salt = os.urandom(16)
        nonce = os.urandom(12)
        kek = CryptoKeyService._derive_kek(password, salt)
        aesgcm = AESGCM(kek)
        ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
        return {
            "ciphertext": ciphertext,
            "salt": salt,
            "nonce": nonce
        }
        
    @staticmethod
    def _decrypt_private_key(enc_dict: dict, password: str) -> bytes:
        """Decrypt a private key."""
        kek = CryptoKeyService._derive_kek(password, enc_dict["salt"])
        aesgcm = AESGCM(kek)
        return aesgcm.decrypt(enc_dict["nonce"], enc_dict["ciphertext"], None)

    @staticmethod
    def issue_user_keys(user, password: str):
        """Generate and store ML-KEM-768 and RSA-2048 keys for a new user."""
        if not _OQS_AVAILABLE:
            raise RuntimeError(
                "liboqs is not installed — cannot generate PQC keys. "
                "Build and install liboqs, then `pip install liboqs-python`."
            )
        
        # 1. Generate ML-KEM-768 keypair
        kem = oqs.KeyEncapsulation('ML-KEM-768')
        kem_public_key = kem.generate_keypair()
        kem_secret_key = kem.export_secret_key()
        kem.free()

        # 2. Generate RSA-2048 keypair
        rsa_private = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        rsa_private_bytes = rsa_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        rsa_public_bytes = rsa_private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # 3. Encrypt private keys
        kem_enc = CryptoKeyService._encrypt_private_key(kem_secret_key, password)
        rsa_enc = CryptoKeyService._encrypt_private_key(rsa_private_bytes, password)

        # 4. Store in DB
        user_keys = UserKeys(
            user_id=user.id,
            kem_public_key=kem_public_key,
            kem_private_key_enc=kem_enc["ciphertext"],
            kem_salt=kem_enc["salt"],
            kem_nonce=kem_enc["nonce"],
            rsa_public_key=rsa_public_bytes,
            rsa_private_key_enc=rsa_enc["ciphertext"],
            rsa_salt=rsa_enc["salt"],
            rsa_nonce=rsa_enc["nonce"]
        )
        db.session.add(user_keys)
        # Note: the caller should commit this transaction

    @staticmethod
    def load_private_keys(user_keys: UserKeys, password: str) -> dict:
        """Decrypt and return private keys in-memory."""
        kem_priv = CryptoKeyService._decrypt_private_key({
            "ciphertext": user_keys.kem_private_key_enc,
            "salt": user_keys.kem_salt,
            "nonce": user_keys.kem_nonce
        }, password)
        
        rsa_priv = CryptoKeyService._decrypt_private_key({
            "ciphertext": user_keys.rsa_private_key_enc,
            "salt": user_keys.rsa_salt,
            "nonce": user_keys.rsa_nonce
        }, password)
        
        return {
            "kem_secret_key": kem_priv,
            "rsa_private_key_pem": rsa_priv
        }
