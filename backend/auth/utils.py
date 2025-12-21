from datetime import datetime, timedelta
import secrets
import hashlib
import string
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from auth.models import User, RefreshToken
from models.app_role import AppRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def create_refresh_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    hashed_token = hash_refresh_token(token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await RefreshToken.create(user_id=user_id, token=hashed_token, expires_at=expires_at)
    return token

async def get_current_user(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials if credentials else request.cookies.get(settings.COOKIE_ACCESS_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


async def get_current_user_optional(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User | None:
    token = credentials.credentials if credentials else request.cookies.get(settings.COOKIE_ACCESS_NAME)
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        return None

    return await User.get_or_none(id=user_id)


def hash_refresh_token(token: str) -> str:
    return hash_token(token)

def hash_password_reset_token(token: str) -> str:
    return hash_token(token)

def generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def require_app_role(app_name: str, allowed_roles: list):
    """Decorator to check if user has required role in specific app"""

    async def role_checker(
        request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        user = await get_current_user(request, credentials)

        # Platform admins bypass app-specific checks
        if user.global_role == "admin":
            return user

        # Get app-specific roles for this user
        app_roles = await AppRole.filter(user_id=user.id, app_name=app_name)
        user_roles = [ar.role for ar in app_roles]

        # Check app-specific roles
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {app_name}. Required roles: {allowed_roles}",
            )

        return user

    return role_checker


async def require_role(required_role: str, current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user has required global role"""
    if current_user.global_role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: {required_role}",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user is admin"""
    if current_user.global_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
