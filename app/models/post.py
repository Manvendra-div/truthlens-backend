from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Post(Base):

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    prediction = Column(String)
    fake_confidence = Column(Float)
    real_confidence = Column(Float)

    created_at = Column(DateTime)

    author_id = Column(Integer, ForeignKey("users.id"))

    author = relationship("User")