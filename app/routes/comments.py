from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models.comment import Comment
from app.schemas.comment_schema import CommentCreate
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("/{post_id}")
async def create_comment(
    post_id: int,
    comment: CommentCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_comment = Comment(
        content=comment.content,
        user_id=user_id,
        post_id=post_id
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.id == new_comment.id)
    )
    return result.scalar_one()


@router.get("/{post_id}")
async def get_comments(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.post_id == post_id)
    )
    return result.scalars().all()


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.delete(comment)
    await db.commit()

    return {"message": "Comment deleted"}