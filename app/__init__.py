"""
Flask application factory for the Quantum-Safe Banking Transaction PoC.
"""
from flask import Flask, jsonify, redirect, url_for, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from config import get_config

db  = SQLAlchemy()
jwt = JWTManager()


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)
    db.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.transaction import transaction_bp
    from app.routes.metrics import metrics_bp
    from app.routes.harvest import harvest_bp
    from app.routes.analytics import analytics_bp
    from app.routes.keys import keys_bp
    from app.routes.peer import peer_bp

    app.register_blueprint(auth_bp,        url_prefix="/api")
    app.register_blueprint(transaction_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp,     url_prefix="/api")
    app.register_blueprint(harvest_bp,     url_prefix="/api")
    app.register_blueprint(analytics_bp,   url_prefix="/api")
    app.register_blueprint(keys_bp,        url_prefix="/api")
    app.register_blueprint(peer_bp,        url_prefix="/api")

    from app.routes.stream import stream_bp
    app.register_blueprint(stream_bp,      url_prefix="/api")

    # Register page routes
    @app.route("/")
    def dashboard():
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/harvest")
    def harvest_page():
        return render_template("harvest.html")

    # ---------------------------------------------------------------------------
    # JWT guard — protect all /api/* routes except /api/auth/*
    # ---------------------------------------------------------------------------
    _PUBLIC_PREFIXES = (
        "/api/auth/",
        "/api/p2p/",   # P2P node-to-node endpoints use HMAC, not JWT
        "/static/",
    )

    @app.before_request
    def enforce_jwt():
        from flask import request
        path = request.path
        # Only guard API routes
        if not path.startswith("/api/"):
            return None
        # Allow public prefixes through
        for prefix in _PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return None
        # Verify JWT — return 401 if missing/invalid
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return jsonify({"error": "Authentication required", "detail": str(exc)}), 401

    # Create database tables
    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()
        _ensure_schema_extensions()

    return app


def _ensure_schema_extensions():
    """Add backward-compatible columns for legacy SQLite databases."""
    try:
        columns = db.session.execute(text("PRAGMA table_info(transactions)")).fetchall()
        existing = {c[1] for c in columns}

        migrations = [
            ("latency_bucket",      "VARCHAR(32)"),
            ("failure_reason",      "VARCHAR(255)"),
            ("encapsulate_time_ms", "FLOAT"),
            ("decapsulate_time_ms", "FLOAT"),
            ("secret_key_bytes",    "INTEGER"),
            ("origin_ip",           "VARCHAR(45)"),
        ]
        for col, typedef in migrations:
            if col not in existing:
                db.session.execute(
                    text(f"ALTER TABLE transactions ADD COLUMN {col} {typedef}")
                )

        db.session.commit()
    except Exception:
        db.session.rollback()
