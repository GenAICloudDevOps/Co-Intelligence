from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from auth.models import User
from auth.utils import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=Token)
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
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await User.get_or_none(email=user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username
    }
