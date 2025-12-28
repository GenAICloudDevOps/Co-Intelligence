from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, HTTPException, status, Depends, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator
from auth.models import User, RefreshToken, PasswordResetToken
from auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_refresh_token,
    hash_password_reset_token,
    generate_temp_password,
)
from config import settings
from services.email_notifications import email_notifications

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
    password: str | None = None
    send_password_email: bool = False
    
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
        if v is None or v == "":
            return v
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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    try:
        # Validate input
        if not user_data.email or not user_data.username:
            raise HTTPException(status_code=400, detail="Email and username required")

        if user_data.send_password_email:
            if not email_notifications.is_configured():
                raise HTTPException(status_code=503, detail="Email service not configured")
            raw_password = generate_temp_password(settings.TEMP_PASSWORD_LENGTH)
        else:
            if not user_data.password:
                raise HTTPException(status_code=400, detail="Password required")
            if len(user_data.password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            raw_password = user_data.password
        
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
            hashed_password=get_password_hash(raw_password)
        )

        if user_data.send_password_email:
            try:
                email_notifications.send_text_email(
                    to_email=user.email,
                    subject="Your Co-Intelligence account password",
                    body=(
                        f"Hello {user.username},\n\n"
                        "Your account has been created. Use this temporary password to log in:\n\n"
                        f"{raw_password}\n\n"
                        "For security, reset your password after logging in.\n"
                    ),
                )
            except Exception as e:
                await user.delete()
                raise HTTPException(status_code=500, detail=f"Failed to send password email: {e}")
        
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

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    if not email_notifications.is_configured():
        raise HTTPException(status_code=503, detail="Email service not configured")
    if not settings.FRONTEND_URL or "localhost" in settings.FRONTEND_URL or "127.0.0.1" in settings.FRONTEND_URL:
        raise HTTPException(status_code=503, detail="Frontend URL not configured")

    email = payload.email.strip()
    user = await User.get_or_none(email=email)
    if user:
        now = datetime.now(timezone.utc)
        await PasswordResetToken.filter(user_id=user.id, used_at__isnull=True).update(used_at=now)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_password_reset_token(raw_token)
        expires_at = now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        await PasswordResetToken.create(user_id=user.id, token=token_hash, expires_at=expires_at)

        reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
        email_notifications.send_text_email_safe(
            to_email=user.email,
            subject="Reset your Co-Intelligence password",
            body=(
                f"Hello {user.username},\n\n"
                "We received a request to reset your password.\n\n"
                f"Reset link: {reset_link}\n\n"
                f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. "
                "If you didn't request this, you can ignore this email.\n"
            ),
        )

    return {"success": True, "message": "If that email exists, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    token = payload.token.strip() if payload.token else ""
    if not token:
        raise HTTPException(status_code=400, detail="Reset token required")
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(payload.password) > 100:
        raise HTTPException(status_code=400, detail="Password must be less than 100 characters")

    token_hash = hash_password_reset_token(token)
    token_record = await PasswordResetToken.get_or_none(token=token_hash)
    now = datetime.now(timezone.utc)
    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if token_record.expires_at < now:
        await token_record.delete()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if token_record.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await User.get_or_none(id=token_record.user_id)
    if not user:
        await token_record.delete()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = get_password_hash(payload.password)
    await user.save(update_fields=["hashed_password"])
    await RefreshToken.filter(user_id=user.id).delete()
    await PasswordResetToken.filter(user_id=user.id, used_at__isnull=True).update(used_at=now)

    return {"success": True}

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


# ─────────────────────────────────────────────────────────────────────────────
# Notification Center & Per-App Preferences
# ─────────────────────────────────────────────────────────────────────────────
from services.in_app_notifications import in_app_notifications
from services.notification_prefs import notification_prefs, NOTIFIABLE_APPS
from pydantic import Field
from typing import Optional, List


class NotificationPrefItem(BaseModel):
    app_id: str
    email_enabled: bool
    in_app_enabled: bool
    slack_enabled: bool = False


class NotificationPrefsUpdatePayload(BaseModel):
    preferences: List[NotificationPrefItem]


@router.get("/notifications")
async def get_notifications(
    limit: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """Get in-app notifications for the current user."""
    notifications = await in_app_notifications.get_user_notifications(
        user_id=current_user.id,
        limit=min(limit, 50),
        unread_only=unread_only,
    )
    return {"notifications": notifications}


@router.get("/notifications/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    """Get count of unread notifications."""
    count = await in_app_notifications.get_unread_count(current_user.id)
    return {"count": count}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    success = await in_app_notifications.mark_as_read(notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: User = Depends(get_current_user)):
    """Mark all notifications as read."""
    count = await in_app_notifications.mark_all_as_read(current_user.id)
    return {"success": True, "count": count}


@router.get("/notifications/preferences")
async def get_notification_preferences(current_user: User = Depends(get_current_user)):
    """Get per-app notification preferences."""
    prefs = await notification_prefs.get_user_prefs(current_user.id)
    return {
        "global_email_enabled": current_user.email_notifications_enabled,
        "apps": NOTIFIABLE_APPS,
        "preferences": prefs,
    }


@router.put("/notifications/preferences")
async def update_notification_preferences(
    payload: NotificationPrefsUpdatePayload,
    current_user: User = Depends(get_current_user),
):
    """Update per-app notification preferences."""
    for pref in payload.preferences:
        if pref.app_id in NOTIFIABLE_APPS:
            await notification_prefs.update_user_pref(
                user_id=current_user.id,
                app_id=pref.app_id,
                email_enabled=pref.email_enabled,
                in_app_enabled=pref.in_app_enabled,
                slack_enabled=pref.slack_enabled,
            )
    # Return updated preferences
    prefs = await notification_prefs.get_user_prefs(current_user.id)
    return {
        "global_email_enabled": current_user.email_notifications_enabled,
        "apps": NOTIFIABLE_APPS,
        "preferences": prefs,
    }

