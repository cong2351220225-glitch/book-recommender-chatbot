from __future__ import annotations

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for the new account")
    password: str = Field(..., min_length=3, max_length=100, description="Password for the account")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str = "user"


class UserOut(BaseModel):
    username: str
    role: str

