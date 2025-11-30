from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from auth.models import User, RefreshToken
from auth.utils import get_password_hash, verify_password, create_access_token, create_refresh_token, get_current_user

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    if await User.exists(email=user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await User.exists(username=user_data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user = await User.create(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password)
    )
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = await create_refresh_token(user.id)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await User.get_or_none(email=user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = await create_refresh_token(user.id)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    token_record = await RefreshToken.get_or_none(token=data.refresh_token)
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
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    await RefreshToken.filter(user_id=current_user.id).delete()
    return {"success": True}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username
    }
