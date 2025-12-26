# agent_v1/api/schemas/auth.py

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class UserStatus(str, Enum):
    job = "job"
    student = "student"
    other = "other"


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str
    email: str
    phone: Optional[str] = None
    current_status: UserStatus
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
