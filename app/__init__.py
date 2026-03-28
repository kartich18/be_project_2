"""
Flask application factory for the Quantum-Safe Banking Transaction PoC.
"""
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from config import get_config

db = SQLAlchemy()


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

    # Register blueprints
    from app.routes.transaction import transaction_bp
    from app.routes.metrics import metrics_bp
    from app.routes.harvest import harvest_bp

    app.register_blueprint(transaction_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp, url_prefix="/api")
    app.register_blueprint(harvest_bp, url_prefix="/api")

    # Register dashboard route
    @app.route("/")
    def dashboard():
        return app.send_static_file("index.html")

    # Create database tables
    with app.app_context():
        from app.models import transaction  # noqa: F401

        db.create_all()

    return app
