from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class ModelName(Base):
    """
    Model description.
    
    Attributes:
        id: Primary key
        name: Name of the item
        description: Detailed description of the item
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """
    __tablename__ = "model_name"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Example relationship
    # parent_id = Column(Integer, ForeignKey("parent.id"), nullable=True)
    # parent = relationship("Parent", back_populates="children")
    # children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f"<ModelName id={self.id} name={self.name}>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 