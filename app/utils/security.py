import time
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import hashlib
import base64
import bcrypt
from app.database import get_db
from app.models.user import User


SECRET_KEY = "hrcgilkmjaXq/mEUX6U7/JycASopaxNRtBUxc1CHqIs="
ALGORITHM = "HS256"


def _prehash(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prehash(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))


def create_access_token(user_id: int):
    expire = int(time.time()) + (60 * 60 * 24)

    payload = {
        "user_id": user_id,
        "exp": expire
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ✅ FULLY ASYNC (correct way)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # ✅ Proper async DB query
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user