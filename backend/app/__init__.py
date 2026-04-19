"""
Flask application factory for the Quantum-Safe Banking Transaction PoC.
"""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

from config import get_config

db  = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()


def create_app(config_class=None):
    """Create and configure the Flask application."""
    # SPA is served entirely by Vite — no static_folder or template_folder needed.
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    # Allow requests from both the Vite dev server and the production SPA origin.
    # In production, replace http://localhost:5173 with your deployed frontend URL.
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    from app.routes.auth import auth_bp
    from app.routes.transaction import transaction_bp
    from app.routes.metrics import metrics_bp
    from app.routes.harvest import harvest_bp
    from app.routes.analytics import analytics_bp
    from app.routes.keys import keys_bp
    from app.routes.clients import clients_bp
    from app.routes.accounts import accounts_bp

    app.register_blueprint(auth_bp,        url_prefix="/api")
    app.register_blueprint(transaction_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp,     url_prefix="/api")
    app.register_blueprint(harvest_bp,     url_prefix="/api")
    app.register_blueprint(analytics_bp,   url_prefix="/api")
    app.register_blueprint(keys_bp,        url_prefix="/api")
    app.register_blueprint(clients_bp,     url_prefix="/api")
    app.register_blueprint(accounts_bp,    url_prefix="/api")

    from app.routes.stream import stream_bp
    app.register_blueprint(stream_bp,      url_prefix="/api")

    # SPA is served by Vite (dev) or a static file host (prod).
    # Root route is kept as a health-check for load balancers and reverse proxies.
    @app.route("/")
    def spa_root():
        return jsonify({"status": "ok", "service": "quantum-safe-bank-api"})

    # ---------------------------------------------------------------------------
    # JWT guard — protect all /api/* routes except /api/auth/*
    # ---------------------------------------------------------------------------
    _PUBLIC_PREFIXES = (
        "/api/auth/",
        "/api/clients/register",   # shared-secret bootstrap, not JWT
        "/static/",
        "/api/stream/",            # SSE endpoints use custom query_token_required
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
        # db.create_all() is removed in favour of Alembic migrations

    return app

