from fastapi import Request, HTTPException
from jose import jwt
from app.utils.security import SECRET_KEY, ALGORITHM


def get_current_user(request: Request):

    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    return payload["user_id"]