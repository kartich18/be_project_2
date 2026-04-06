"""
Central configuration for the Quantum-Safe Banking Transaction PoC.
"""
import os
import socket
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _get_lan_ip() -> str:
    """Best-effort detection of the machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'transactions.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cryptography settings
    CLASSICAL_ALGORITHM = "RSA-2048"
    RSA_KEY_SIZE = 2048

    PQC_KEM_ALGORITHM = "ML-KEM-768"  # FIPS 203 (formerly Kyber-768)
    AES_KEY_SIZE = 256  # bits, for AES-256-GCM symmetric encryption

    # Benchmark defaults
    BENCHMARK_DEFAULT_ITERATIONS = 100
    BENCHMARK_MAX_ITERATIONS = 10000

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.path.join(BASE_DIR, "app.log")

    # ── JWT Authentication ────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-dev-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME    = "Authorization"
    JWT_HEADER_TYPE    = "Bearer"

    # ── P2P Node Authentication (HMAC-SHA256) ─────────────────────────────
    # Both nodes must share the same secret (set in .env on each machine)
    PEER_HMAC_SECRET = os.environ.get("PEER_HMAC_SECRET", "peer-hmac-secret-change-in-production")
    PEER_REQUEST_TIMEOUT = 5  # seconds

    # ── TLS ───────────────────────────────────────────────────────────────
    TLS_CERT = os.path.join(BASE_DIR, "cert.pem")
    TLS_KEY  = os.path.join(BASE_DIR, "key.pem")

    # ── Node Identity ─────────────────────────────────────────────────────
    NODE_PORT = int(os.environ.get("NODE_PORT", 5000))
    NODE_IP   = os.environ.get("NODE_IP", _get_lan_ip())


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


# Config mapping
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
