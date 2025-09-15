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
from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Validate all required environment variables
validate_all_required_env()

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Initialize extensions
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models first (they create the db instance)
from models import (
    Application,
    AuditLog,
    Package,
    PackageReference,
    PackageRequest,
    PackageValidation,
    SupportedLicense,
    User,
    db,
)

# Now initialize the database with the app
db.init_app(app)

from routes.admin_routes import admin_bp

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.package_routes import package_bp

app.register_blueprint(auth_bp)
app.register_blueprint(package_bp)
app.register_blueprint(admin_bp)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


def wait_for_db(max_retries=30, delay=2):
    """Wait for database to be ready"""
    import time

    for attempt in range(max_retries):
        try:
            with app.app_context():
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


if __name__ == "__main__":
    # Wait for database to be ready
    wait_for_db()

    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")

    app.run(host="0.0.0.0", port=5000, debug=True)
