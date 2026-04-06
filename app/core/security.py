from passlib.context import CryptContext

# Define the bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verifies an incoming plain-text API key against the stored bcrypt hash.
    """
    return pwd_context.verify(plain_key, hashed_key)