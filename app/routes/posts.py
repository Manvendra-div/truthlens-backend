from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.post import Post
from app.models.comment import Comment
from app.models.user import User

from app.schemas.post_schema import PostCreateSchema
from app.utils.security import get_current_user
from app.services.dedup_service import check_duplicate, compute_hash
from fastapi import HTTPException

from app.services.model_service import predict_news

router = APIRouter(prefix="/posts", tags=["posts"])


# ===============================
# CREATE POST
# ===============================

@router.post("/")
def create_post(
        post: PostCreateSchema,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = check_duplicate(db, post.title, post.content)
    if result.is_duplicate:
        detail = {
            "error": "duplicate_post",
            "kind": result.kind,
            "message": "A very similar article already exists on the platform.",
        }
        if result.duplicate_of:
            detail["duplicate_of_post_id"] = result.duplicate_of
        raise HTTPException(status_code=409, detail=detail)

    # Run AI prediction
    prediction = predict_news(post.content)

    new_post = Post(
        title=post.title,
        content=post.content,
        author_id=current_user.id,
        prediction=prediction["label"],
        fake_confidence=prediction["fake_confidence"],
        real_confidence=prediction["real_confidence"],
        created_at=datetime.utcnow()
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return {"message": "Post created successfully"}


# ===============================
# GET ALL POSTS (FEED)
# ===============================

@router.get("/")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()

    result = []

    for post in posts:
        comments_count = db.query(Comment) \
            .filter(Comment.post_id == post.id) \
            .count()

        result.append({
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

    return result


# ===============================
# GET SINGLE POST
# ===============================

@router.get("/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comments_count = db.query(Comment) \
        .filter(Comment.post_id == post.id) \
        .count()

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
def delete_post(
        post_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully"}