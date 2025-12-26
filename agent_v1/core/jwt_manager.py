import json
from uuid import uuid4
from datetime import timedelta

import jwt

from agent_v1.api.db.config import Config
from agent_v1.core.errors import AuthError, TokenError
from agent_v1.tools.utils import get_current_utc


class JWTManager:
    """
    Central JWT creation / verification utility.

    - Uses PyJWT only
    - Timestamp-safe
    - Access / Refresh separation enforced
    """

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    @staticmethod
    def _config():
        return Config

    @staticmethod
    def _encode(payload: dict, expires_in_minutes: int) -> dict:
        now = get_current_utc()
        jti = str(uuid4())

        issued_at = int(now.timestamp())
        expires_at = int((now + timedelta(minutes=expires_in_minutes)).timestamp())

        data = json.loads(json.dumps(payload, default=str))
        data.update(
            {
                "jti": jti,
                "iat": issued_at,
                "exp": expires_at,
            }
        )

        token = jwt.encode(
            data,
            JWTManager._config().JWT_SECRET_KEY,
            algorithm=JWTManager._config().JWT_ALGORITHM,
        )

        return {
            "token": token,
            "expires_at": expires_at,
            "jti": jti,
        }

    # --------------------------------------------------
    # Token creation
    # --------------------------------------------------

    @staticmethod
    def create_access_token(payload: dict) -> dict:
        payload = payload.copy()
        payload["token_type"] = "access"

        return JWTManager._encode(
            payload,
            JWTManager._config().ACCESS_TOKEN_EXPIRY_IN_MINUTES,
        )

    @staticmethod
    def create_refresh_token(payload: dict) -> dict:
        payload = payload.copy()
        payload["token_type"] = "refresh"

        expiry_minutes = (
            JWTManager._config().REFRESH_TOKEN_EXPIRY_IN_DAYS * 24 * 60
        )

        return JWTManager._encode(payload, expiry_minutes)

    # --------------------------------------------------
    # Token verification / decoding
    # --------------------------------------------------

    @staticmethod
    def verify_token(token: str) -> bool:
        try:
            jwt.decode(
                token,
                JWTManager._config().JWT_SECRET_KEY,
                algorithms=[JWTManager._config().JWT_ALGORITHM],
                options={"verify_exp": True},
            )
            return True
        except jwt.PyJWTError:
            return False

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                JWTManager._config().JWT_SECRET_KEY,
                algorithms=[JWTManager._config().JWT_ALGORITHM],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            raise TokenError("Token expired").to_http_exception()
        except jwt.InvalidTokenError:
            raise AuthError("Invalid token").to_http_exception()
