from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.core.database import load_users, save_users
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from backend.schemas.auth_schema import UserRegister, UserLogin, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister) -> TokenResponse:
    username = user_data.username.strip()
    users = load_users()
    if username in users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    hashed = hash_password(user_data.password)
    # Store both password and hashed_password for seamless compatibility with Streamlit & FastAPI
    users[username] = {
        "password": user_data.password,
        "hashed_password": hashed,
        "role": "user",
    }
    save_users(users)

    access_token = create_access_token(data={"sub": username, "role": "user"})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=username,
        role="user",
    )


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin) -> TokenResponse:
    username = user_data.username.strip()
    users = load_users()
    user_record = users.get(username)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check hashed_password or password
    stored_hash = user_record.get("hashed_password")
    stored_plain = user_record.get("password")
    is_valid = False
    if stored_hash and verify_password(user_data.password, stored_hash):
        is_valid = True
    elif stored_plain and verify_password(user_data.password, stored_plain):
        is_valid = True
        # Transparently upgrade to bcrypt hash
        user_record["hashed_password"] = hash_password(user_data.password)
        save_users(users)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    role = user_record.get("role", "admin" if username in {"cong1", "admin"} else "user")
    access_token = create_access_token(data={"sub": username, "role": role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=username,
        role=role,
    )


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """OAuth2 password form compatible endpoint for Swagger UI authorization."""
    return login(UserLogin(username=form_data.username, password=form_data.password))


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: dict[str, Any] = Depends(get_current_user)) -> UserOut:
    return UserOut(
        username=current_user["username"],
        role=current_user.get("role", "user"),
    )

