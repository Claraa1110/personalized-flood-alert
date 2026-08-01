import logging
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.supabase_client import supabase_admin

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class CurrentUser:
    user_id: str
    email: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    token = credentials.credentials
    try:
        # 使用 service_role client 驗證，不受 anon key 限制
        response = supabase_admin.auth.get_user(token)
        user = response.user
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        raise _UNAUTHORIZED

    if user is None:
        logger.warning("Token verification returned no user")
        raise _UNAUTHORIZED

    return CurrentUser(user_id=str(user.id), email=user.email or "")
