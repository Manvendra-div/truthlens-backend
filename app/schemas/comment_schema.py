from pydantic import BaseModel
from app.schemas.post_schema import UserResponse


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    post_id: int
    created_at: str
    user: UserResponse

    class Config:
        orm_mode = True