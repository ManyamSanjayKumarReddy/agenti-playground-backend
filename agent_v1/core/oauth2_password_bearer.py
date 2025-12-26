from fastapi.security import OAuth2PasswordBearer


def get_oauth2_scheme() -> OAuth2PasswordBearer:
    """
    OAuth2 scheme used only for extracting Bearer tokens
    from Authorization headers.

    Token URL is informational (Swagger UI).
    """
    return OAuth2PasswordBearer(
        tokenUrl="/auth/login",
        auto_error=True,
    )
