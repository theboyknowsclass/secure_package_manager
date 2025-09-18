"""
Database package for the secure package manager.

This package contains all database-related functionality including:
- Pure SQLAlchemy models (in models/ subpackage)
- Database service for workers
- Flask-SQLAlchemy integration for the main app
"""

# Import Flask-SQLAlchemy only when needed (for Flask app)
try:
    from flask_sqlalchemy import SQLAlchemy

    # Create a SQLAlchemy instance for Flask integration
    db = SQLAlchemy()
except ImportError:
    # Flask-SQLAlchemy not available (e.g., in workers)
    db = None
