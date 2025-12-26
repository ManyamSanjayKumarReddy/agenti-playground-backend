from pydantic import BaseModel
from typing import Literal


class SignupRequest(BaseModel):
    username: str
    name: str
    email: str
    phone: str
    current_status: Literal["job", "student", "other"]
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str


class AuthPayload(BaseModel):
    sub: str
    username: str
    is_admin: bool
    token_type: str
    jti: str
    exp: int
