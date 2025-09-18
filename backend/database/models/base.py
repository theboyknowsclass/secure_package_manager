"""
Base model class for SQLAlchemy models
"""

from sqlalchemy.ext.declarative import declarative_base

# Create a declarative base for pure SQLAlchemy models
Base = declarative_base()
