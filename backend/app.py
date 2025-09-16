import logging
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
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = FLASK_SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # Initialize extensions with explicit CORS configuration
    CORS(app, 
         origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         supports_credentials=True)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Import models first (they create the db instance)
    from models import (
        AuditLog,
        Package,
        Request,
        SecurityScan,
        SupportedLicense,
        User,
        db,
    )

    # Now initialize the database with the app
    db.init_app(app)

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
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


def wait_for_db(max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for database to be ready"""
    import time
    import logging
    
    logger = logging.getLogger(__name__)

    for attempt in range(max_retries):
        try:
            with app.app_context():
                # Import db inside the app context
                from models import db
                with db.engine.connect() as connection:
                    connection.execute(db.text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt + 1} failed: {str(e)}"
            )
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logger.error("Failed to connect to database after all retries")
                raise e
    return False


if __name__ == "__main__":
    # Wait for database to be ready
    wait_for_db()

    with app.app_context():
        # Import db inside the app context
        from models import db
        db.create_all()
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database tables created/verified")

    app.run(host="0.0.0.0", port=5000, debug=True)
