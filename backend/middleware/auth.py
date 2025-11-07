from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from config import settings
from auth.models import User
from models.app_role import AppRole

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = await User.get_or_none(id=int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user

def require_app_role(app_name: str, allowed_roles: list):
    """Decorator to check if user has required role in specific app"""
    async def role_checker(credentials: HTTPAuthorizationCredentials = Depends(security)):
        user = await get_current_user(credentials)
        
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
                detail=f"Insufficient permissions for {app_name}. Required roles: {allowed_roles}"
            )
        
        return user
    return role_checker

async def require_role(required_role: str, current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user has required global role"""
    if current_user.global_role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: {required_role}"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user is admin"""
    if current_user.global_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
