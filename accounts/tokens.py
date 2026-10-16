"""Access + refresh JWTs signed with separate secrets (Express-compatible)."""

from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


class TokenError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: int, role: str) -> str:
    payload = {
        'userId': user_id,
        'role': role,
        'type': 'access',
        'iat': _now(),
        'exp': _now() + timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES),
    }
    return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET, algorithm='HS256')


def create_refresh_token(*, user_id: int, role: str) -> str:
    payload = {
        'userId': user_id,
        'role': role,
        'type': 'refresh',
        'iat': _now(),
        'exp': _now() + timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS),
    }
    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm='HS256')


def issue_tokens_for_user(user) -> tuple[str, str]:
    access = create_access_token(user_id=user.pk, role=user.role)
    refresh = create_refresh_token(user_id=user.pk, role=user.role)
    return access, refresh


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.ACCESS_TOKEN_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError('Access token expired') from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError('Invalid access token') from exc

    if payload.get('type') != 'access':
        raise TokenError('Invalid access token type')
    if not payload.get('userId'):
        raise TokenError('Invalid access token payload')
    return payload


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.REFRESH_TOKEN_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError('Refresh token expired') from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError('Invalid refresh token') from exc

    if payload.get('type') != 'refresh':
        raise TokenError('Invalid refresh token type')
    if not payload.get('userId'):
        raise TokenError('Invalid refresh token payload')
    return payload
