from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from app.database import get_db
from app.models.post import Post
from app.models.comment import Comment
from app.models.user import User
from app.schemas.post_schema import PostCreateSchema
from app.utils.security import get_current_user
from app.services.dedup_service import check_duplicate, compute_hash
from app.services.model_service import predict_news

router = APIRouter(prefix="/posts", tags=["posts"])


# ===============================
# CREATE POST
# ===============================

@router.post("/")
async def create_post(
    post: PostCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await check_duplicate(db, post.title, post.content)
    if result.is_duplicate:
        detail = {
            "error": "duplicate_post",
            "kind": result.kind,
            "message": "A very similar article already exists on the platform.",
        }
        if result.duplicate_of:
            detail["duplicate_of_post_id"] = result.duplicate_of
        raise HTTPException(status_code=409, detail=detail)

    prediction = predict_news(post.content)

    new_post = Post(
        title=post.title,
        content=post.content,
        author_id=current_user.id,
        prediction=prediction["label"],
        fake_confidence=prediction["fake_confidence"],
        real_confidence=prediction["real_confidence"],
        content_hash=compute_hash(post.title, post.content),
        created_at=datetime.utcnow()
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    return {"message": "Post created successfully"}


# ===============================
# GET ALL POSTS (FEED)
# ===============================

@router.get("/")
async def get_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post)
        .options(joinedload(Post.author))
        .order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()

    output = []
    for post in posts:
        comments_result = await db.execute(
            select(Comment).where(Comment.post_id == post.id)
        )
        comments_count = len(comments_result.scalars().all())

        output.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": {
                "id": post.author.id,
                "username": post.author.username,
                "email": post.author.email
            },
            "prediction": {
                "label": post.prediction,
                "fake_confidence": post.fake_confidence,
                "real_confidence": post.real_confidence
            },
            "comments_count": comments_count,
            "created_at": post.created_at
        })

    return output


# ===============================
# GET SINGLE POST
# ===============================

@router.get("/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post)
        .options(joinedload(Post.author))
        .where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comments_result = await db.execute(
        select(Comment).where(Comment.post_id == post.id)
    )
    comments_count = len(comments_result.scalars().all())

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "email": post.author.email
        },
        "prediction": {
            "label": post.prediction,
            "fake_confidence": post.fake_confidence,
            "real_confidence": post.real_confidence
        },
        "comments_count": comments_count,
        "created_at": post.created_at
    }


# ===============================
# DELETE POST
# ===============================

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(post)
    await db.commit()

    return {"message": "Post deleted successfully"}