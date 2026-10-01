import bcrypt


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = password.encode("utf-8")
        if len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, UnicodeError, TypeError):
        return False
