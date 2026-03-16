from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session,joinedload
from app.database import get_db
from app.models.comment import Comment
from app.schemas.comment_schema import CommentCreate
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/comments",
    tags=["comments"]
)

@router.post("/{post_id}")
def create_comment(
    post_id: int,
    comment: CommentCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    new_comment = Comment(
        content=comment.content,
        user_id=user_id,
        post_id=post_id
    )

    db.add(new_comment)
    db.commit()

    created_comment = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.id == new_comment.id)
        .first()
    )

    return created_comment

@router.get("/{post_id}")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).options(joinedload(Comment.user)).filter(Comment.post_id == post_id).all()
    return comments

@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    db.delete(comment)
    db.commit()

    return {"message": "Comment deleted"}