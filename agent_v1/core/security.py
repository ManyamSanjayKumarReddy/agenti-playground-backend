from passlib.context import CryptContext

_password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def generate_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return _password_context.hash(password)


def compare_password(password: str, hashed_password: str) -> bool:
    """
    Verify plaintext password against stored hash.
    """
    return _password_context.verify(password, hashed_password)
