from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator
from auth.models import User, RefreshToken
from auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_refresh_token,
)
from config import settings

router = APIRouter()


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_ACCESS_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower(),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=settings.COOKIE_DOMAIN,
        path=settings.COOKIE_PATH,
    )
    response.set_cookie(
        key=settings.COOKIE_REFRESH_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE.lower(),
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        domain=settings.COOKIE_DOMAIN,
        path=settings.COOKIE_PATH,
    )


def _clear_auth_cookies(response: JSONResponse) -> None:
    response.delete_cookie(
        key=settings.COOKIE_ACCESS_NAME,
        domain=settings.COOKIE_DOMAIN,
        path=settings.COOKIE_PATH,
    )
    response.delete_cookie(
        key=settings.COOKIE_REFRESH_NAME,
        domain=settings.COOKIE_DOMAIN,
        path=settings.COOKIE_PATH,
    )

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    
    @validator('username')
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if len(v) > 100:
            raise ValueError('Password must be less than 100 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class PreferencesUpdate(BaseModel):
    email_notifications_enabled: bool

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    try:
        # Validate input
        if not user_data.email or not user_data.username or not user_data.password:
            raise HTTPException(status_code=400, detail="Email, username, and password required")
        
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Check if email exists
        existing_email = await User.exists(email=user_data.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username exists
        existing_username = await User.exists(username=user_data.username)
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Create user
        user = await User.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password)
        )
        
        # Create tokens
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = await create_refresh_token(user.id)
        
        response = JSONResponse(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }
        )
        _set_auth_cookies(response, access_token, refresh_token)
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in register: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    try:
        user = await User.get_or_none(email=user_data.email)
        if not user or not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = await create_refresh_token(user.id)
        response = JSONResponse(
            {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
        )
        _set_auth_cookies(response, access_token, refresh_token)
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in login: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, data: RefreshRequest | None = Body(default=None)):
    raw_refresh = data.refresh_token if data and data.refresh_token else request.cookies.get(settings.COOKIE_REFRESH_NAME)
    token_record = await RefreshToken.get_or_none(token=hash_refresh_token(raw_refresh)) if raw_refresh else None
    if not token_record or token_record.expires_at < datetime.utcnow():
        if token_record:
            await token_record.delete()
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user = await User.get_or_none(id=token_record.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Delete old refresh token and create new one
    await token_record.delete()
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = await create_refresh_token(user.id)
    response = JSONResponse(
        {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
    )
    _set_auth_cookies(response, access_token, new_refresh_token)
    return response

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    await RefreshToken.filter(user_id=current_user.id).delete()
    response = JSONResponse({"success": True})
    _clear_auth_cookies(response)
    return response

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "global_role": current_user.global_role,
        "email_notifications_enabled": current_user.email_notifications_enabled,
    }

@router.put("/me/preferences")
async def update_preferences(payload: PreferencesUpdate, current_user: User = Depends(get_current_user)):
    current_user.email_notifications_enabled = payload.email_notifications_enabled
    await current_user.save(update_fields=["email_notifications_enabled"])
    return {"email_notifications_enabled": current_user.email_notifications_enabled}
