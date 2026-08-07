"""Password hashing and session-token primitives.

- Argon2id (argon2-cffi defaults) for passwords: memory-hard, the current
  OWASP recommendation for password storage.
- Session tokens are 256-bit random values. The browser gets the raw token
  (in an HttpOnly cookie); the database stores only sha256(token), so a
  database leak does not yield usable cookies.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()  # argon2id with library defaults


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, candidate: str) -> bool:
    try:
        return _hasher.verify(password_hash, candidate)
    except VerifyMismatchError:
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
