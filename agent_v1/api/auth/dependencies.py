# agent_v1/api/auth/dependencies.py

from typing import Annotated
from fastapi import Depends

from agent_v1.core.jwt_manager import JWTManager
from agent_v1.api.db.models import User
from agent_v1.api.auth.schemas import AuthPayload
from agent_v1.core.oauth2_password_bearer import get_oauth2_scheme
from agent_v1.core.errors import AuthError

oauth2_scheme = get_oauth2_scheme()


class AuthDependency:

    @staticmethod
    async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
    ) -> User:
        try:
            payload = JWTManager.decode_token(token)
            data = AuthPayload(**payload)

            # Enforce access token usage only
            if data.token_type != "access":
                raise AuthError("Invalid token type")

            user = await User.get_or_none(
                id=data.sub,
                is_active=True,
            )

            if not user:
                raise AuthError("Invalid authentication")

            return user

        except AuthError:
            raise
        except Exception:
            # Catch malformed / expired / tampered tokens
            raise AuthError("Invalid authentication").to_http_exception()

    current_user = Annotated[User, Depends(get_current_user)]


class AdminOnly:
    def __call__(self, user: AuthDependency.current_user):
        if not user.is_admin:
            raise AuthError("Admin access required").to_http_exception()
        return True
