from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    username = Column(String)
    password_hash = Column(String, nullable=True)
    google_id = Column(String, nullable=True)
    comments = relationship("Comment", back_populates="user")