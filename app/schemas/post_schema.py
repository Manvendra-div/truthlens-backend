from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True


class PredictionResponse(BaseModel):
    label: str
    fake_confidence: float
    real_confidence: float


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author: UserResponse
    prediction: PredictionResponse
    comments_count: int
    created_at: datetime

    class Config:
        orm_mode = True


class PostCreateSchema(BaseModel):
  title: str
  content: str