# agent_v1/api/auth/routes.py

from fastapi import APIRouter, status, Depends

from agent_v1.api.auth.schemas import (
    SignupRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    AccessTokenResponse,
)
from agent_v1.api.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(payload: SignupRequest):
    return await AuthService.signup(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(payload: LoginRequest):
    return await AuthService.login(payload)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(payload: RefreshTokenRequest):
    return await AuthService.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(payload: RefreshTokenRequest):
    await AuthService.logout(payload.refresh_token)
    return None
