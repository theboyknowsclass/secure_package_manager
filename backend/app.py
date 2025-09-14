from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models first (they create the db instance)
from models import db, User, Application, SupportedLicense, PackageRequest, Package, PackageValidation, PackageReference, AuditLog

# Now initialize the database with the app
db.init_app(app)

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.package_routes import package_bp
from routes.admin_routes import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(package_bp)
app.register_blueprint(admin_bp)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

def wait_for_db(max_retries=30, delay=2):
    """Wait for database to be ready"""
    import time
    for attempt in range(max_retries):
        try:
            with app.app_context():
                with db.engine.connect() as connection:
                    connection.execute(db.text('SELECT 1'))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logger.error("Failed to connect to database after all retries")
                raise e

if __name__ == '__main__':
    # Wait for database to be ready
    wait_for_db()
    
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
