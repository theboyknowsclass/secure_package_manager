import logging
import os
from datetime import datetime

# Import centralized configuration
from config.constants import (
    DATABASE_URL,
    FLASK_SECRET_KEY,
    MAX_CONTENT_LENGTH,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    validate_all_required_env,
)
from dotenv import load_dotenv
from flask import Flask, Response, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Validate all required environment variables
validate_all_required_env()


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = FLASK_SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # Initialize extensions with explicit CORS configuration
    CORS(
        app,
        origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.30.105:3000"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        supports_credentials=True,
    )

    # Configure logging - only show errors and warnings in production
    log_level = logging.ERROR if os.getenv("FLASK_ENV") == "production" else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Suppress noisy loggers
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)

    # Database will be initialized per-request using DatabaseService

    from routes.admin_routes import admin_bp
    from routes.approver_routes import approver_bp

    # Import and register blueprints
    from routes.auth_routes import auth_bp
    from routes.package_routes import package_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(package_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(approver_bp)

    return app


# Create the app instance
app = create_app()


@app.route("/health", methods=["GET"])
def health_check() -> Response:
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/heartbeat", methods=["GET"])
def heartbeat() -> Response:
    """Heartbeat endpoint for monitoring."""
    # Only log heartbeat in production if specifically requested
    if os.getenv("FLASK_ENV") == "production" and os.getenv("LOG_HEARTBEATS", "false").lower() == "true":
        logging.info("API heartbeat check")

    return jsonify(
        {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "secure-package-manager-api",
        }
    )


def wait_for_db(max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for database to be ready."""
    import time

    from database.service import DatabaseService

    for attempt in range(max_retries):
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required")

            db_service = DatabaseService(database_url)
            if db_service.test_connection():
                # Only log successful connection in development
                if os.getenv("FLASK_ENV") != "production":
                    logging.info("Database connection successful")
                return True
        except Exception as e:
            logging.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logging.error("Failed to connect to database after all retries")
                raise e
    return False


if __name__ == "__main__":
    # Wait for database to be ready
    wait_for_db()

    # Create database tables using pure SQLAlchemy
    from database.models import Base
    from sqlalchemy import create_engine

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        # Only log table creation in development
        if os.getenv("FLASK_ENV") != "production":
            logging.getLogger(__name__).info("Database tables created/verified")

    app.run(host="0.0.0.0", port=5000, debug=True)
