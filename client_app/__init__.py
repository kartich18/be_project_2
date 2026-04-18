"""
client_app — thin Flask application running on each client node.

This app is completely independent of ``app/`` (the central server).
It does not share models, blueprints, or DB with the server.
Each instance is identified by a CLIENT_ID injected at startup via
``run_client.py``.

Configuration keys (set by run_client.py before calling create_client_app):
    CLIENT_ID      — e.g. "C1"
    CLIENT_PORT    — the port this app listens on, e.g. 5001
    SERVER_URL     — base URL of the central server, e.g. "http://127.0.0.1:5000"
    CLIENT_REGISTRATION_SECRET — shared secret for auto-registration
"""
import os
from typing import Optional

from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

client_db = SQLAlchemy()


def create_client_app(config_overrides: Optional[dict] = None) -> Flask:
    """Create and configure the client Flask application."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="../static",   # reuse the same CSS/JS assets
    )

    # --- Defaults -----------------------------------------------------------
    app.config["SECRET_KEY"]    = os.environ.get("SECRET_KEY", "client-dev-secret")
    app.config["CLIENT_ID"]     = os.environ.get("CLIENT_ID", "C1")
    app.config["CLIENT_PORT"]   = int(os.environ.get("CLIENT_PORT", 5001))
    app.config["SERVER_URL"]    = os.environ.get("SERVER_URL", "http://127.0.0.1:5000")
    app.config["CLIENT_REGISTRATION_SECRET"] = os.environ.get(
        "CLIENT_REGISTRATION_SECRET", "client-reg-secret-change-in-production"
    )

    # Per-client SQLite stored inside client_app/instance/<client_id>.db
    instance_dir = os.path.join(os.path.dirname(__file__), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    client_id = app.config["CLIENT_ID"]
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(instance_dir, client_id + '.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Apply any runtime overrides (from run_client.py CLI args)
    if config_overrides:
        app.config.update(config_overrides)

    # --- Extensions ---------------------------------------------------------
    client_db.init_app(app)

    # --- Blueprints ---------------------------------------------------------
    from client_app.routes.auth        import client_auth_bp
    from client_app.routes.transaction import client_tx_bp
    from client_app.routes.stream      import client_stream_bp

    app.register_blueprint(client_auth_bp)
    app.register_blueprint(client_tx_bp)
    app.register_blueprint(client_stream_bp)

    # --- DB tables ----------------------------------------------------------
    with app.app_context():
        client_db.create_all()

    return app
