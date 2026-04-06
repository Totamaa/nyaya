from passlib.context import CryptContext

from app.core.config.logs import get_logger

logger = get_logger()

pwd_context = CryptContext(
    schemes=["argon2"], 
    deprecated="auto",
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    is_valid = pwd_context.verify(plain_password, hashed_password)
    need_rehash = pwd_context.needs_update(hashed_password)
    return is_valid, need_rehash
