"""
Central configuration for the Quantum-Safe Banking Transaction PoC.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'transactions.db')}"
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
