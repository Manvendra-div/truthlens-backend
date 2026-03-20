from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os
from app.models.user import User
from app.schemas.auth_schema import SignupSchema, LoginSchema,GoogleTokenPayload
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post("/google")
def google_login(
    payload: GoogleTokenPayload,
    response: Response,
    db: Session = Depends(get_db)
):
    # ── verify Google token ───────────────────────────────────────
    try:
        info = id_token.verify_oauth2_token(
            payload.token,
            grequests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    email     = info.get("email")
    name      = info.get("name", email.split("@")[0])
    google_id = info.get("sub")   # unique Google user ID

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # ── find or create user ───────────────────────────────────────
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # brand new user — create from Google profile
        user = User(
            username      = name,
            email         = email,
            google_id     = google_id,
            password_hash = "",   # Google users have no password
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    elif not user.google_id:
        # existing email/password user — link Google account
        user.google_id = google_id
        db.commit()

    # ── issue your normal JWT ─────────────────────────────────────
    access_token = create_access_token(user.id)

    response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    samesite="lax",
    secure=False,      # False for localhost HTTP
    max_age=86400,     # 1 day
    path="/",          # ← make sure cookie is sent on all routes
    )

    return {
        "message": "logged in",
        "user": {
            "id":       user.id,
            "username": user.username,
            "email":    user.email,
        }
    }

@router.post("/signup")
def signup(user: SignupSchema, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully"
    }

@router.post("/login")
def login(user: LoginSchema, response: Response, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(db_user.id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}

@router.get("/me")
def check_auth(current_user = Depends(get_current_user)):
    return current_user