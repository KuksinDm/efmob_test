import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


def _now():
    return datetime.now(timezone.utc)


def create_token(user_id: uuid.UUID, token_type: str, exp_delta: timedelta) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_access_token(user_id: uuid.UUID) -> str:
    return create_token(
        user_id, "access", timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
    )


def generate_refresh_token(user_id: uuid.UUID) -> str:
    return create_token(
        user_id, "refresh", timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    )


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
        leeway=5,
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload
