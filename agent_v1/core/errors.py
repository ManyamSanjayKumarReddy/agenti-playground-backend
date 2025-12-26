from fastapi import HTTPException, status


class AppError(HTTPException):
    """
    Base application error.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        super().__init__(status_code=status_code, detail=message)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail=self.message,
        )


class AuthError(AppError):
    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ):
        super().__init__(message, status_code)


class TokenError(AppError):
    def __init__(
        self,
        message: str = "Invalid or expired token",
        status_code: int = status.HTTP_403_FORBIDDEN,
    ):
        super().__init__(message, status_code)


class AlreadyExistError(AppError):
    def __init__(
        self,
        message: str = "Resource already exists",
        status_code: int = status.HTTP_409_CONFLICT,
    ):
        super().__init__(message, status_code)


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message, status_code)


class BadRequestError(AppError):
    def __init__(
        self,
        message: str = "Bad request",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(message, status_code)
