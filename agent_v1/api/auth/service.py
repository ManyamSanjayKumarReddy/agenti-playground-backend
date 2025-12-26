from tortoise.transactions import atomic
from tortoise.exceptions import IntegrityError, DoesNotExist

from agent_v1.api.db.models import User, RefreshToken
from agent_v1.api.auth.schemas import SignupRequest, LoginRequest
from agent_v1.core.security import generate_password_hash, compare_password
from agent_v1.core.jwt_manager import JWTManager
from agent_v1.core.errors import AuthError, AlreadyExistError, TokenError
from agent_v1.tools.utils import get_current_utc


class AuthService:

    # --------------------------------------------------
    # Signup
    # --------------------------------------------------

    @staticmethod
    @atomic()
    async def signup(data: SignupRequest):
        try:
            user = await User.create(
                username=data.username,
                name=data.name,
                email=data.email,
                phone=data.phone,
                current_status=data.current_status,
                password_hash=generate_password_hash(data.password),
                is_admin=False,
                is_active=True,
            )
        except IntegrityError:
            raise AlreadyExistError(
                "Username / Email / Phone already exists"
            ).to_http_exception()

        return await AuthService._issue_tokens(user)

    # --------------------------------------------------
    # Login
    # --------------------------------------------------

    @staticmethod
    async def login(data: LoginRequest):
        try:
            user = await User.get(username=data.username, is_active=True)
        except DoesNotExist:
            raise AuthError("Invalid username or password").to_http_exception()

        if not compare_password(data.password, user.password_hash):
            raise AuthError("Invalid username or password").to_http_exception()

        return await AuthService._issue_tokens(user)

    # --------------------------------------------------
    # Token issuing
    # --------------------------------------------------

    @staticmethod
    async def _issue_tokens(user: User):
        access = JWTManager.create_access_token(
            {
                "sub": str(user.id),
                "username": user.username,
                "is_admin": user.is_admin,
            }
        )

        refresh = JWTManager.create_refresh_token(
            {
                "sub": str(user.id),
            }
        )

        await RefreshToken.create(
            user=user,
            hashed_token=generate_password_hash(refresh["token"]),
            jti=refresh["jti"],
            expires_at=refresh["expires_at"],
            is_revoked=False,
        )

        return {
            "access_token": access["token"],
            "refresh_token": refresh["token"],
        }

    # --------------------------------------------------
    # Refresh access token
    # --------------------------------------------------

    @staticmethod
    @atomic()
    async def refresh(refresh_token: str):
        if not JWTManager.verify_token(refresh_token):
            raise TokenError("Invalid refresh token").to_http_exception()

        payload = JWTManager.decode_token(refresh_token)

        token = await RefreshToken.get_or_none(
            jti=payload["jti"],
            is_revoked=False,
        ).select_related("user")

        if not token or token.expires_at < get_current_utc():
            raise TokenError("Refresh token expired").to_http_exception()

        if not compare_password(refresh_token, token.hashed_token):
            raise TokenError("Invalid refresh token").to_http_exception()

        user = token.user

        access = JWTManager.create_access_token(
            {
                "sub": str(user.id),
                "username": user.username,
                "is_admin": user.is_admin,
            }
        )

        return {
            "access_token": access["token"],
        }

    # --------------------------------------------------
    # Logout
    # --------------------------------------------------

    @staticmethod
    async def logout(refresh_token: str):
        payload = JWTManager.decode_token(refresh_token)

        token = await RefreshToken.get_or_none(jti=payload["jti"])
        if token:
            token.is_revoked = True
            await token.save()
