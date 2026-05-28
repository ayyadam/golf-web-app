"""Bearer token authentication for the JSON API.

Tokens are itsdangerous-signed strings (no DB column needed for storage).
They expire after TOKEN_TTL_SECONDS. Verification happens via the
HTTPTokenAuth hook below — APIFlask routes decorated with
@api_bp.auth_required(token_auth) require a valid token.
"""
from apiflask import HTTPTokenAuth
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..models import Member


TOKEN_TTL_SECONDS = 3600  # 1 hour
TOKEN_SALT = 'api-v1-token'


def _serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'], salt=TOKEN_SALT
    )


def issue_token(member_id: int) -> str:
    """Mint a signed token for the given member id."""
    return _serializer().dumps({'member_id': member_id})


def verify_token_str(token: str):
    """Return the Member referenced by a valid token, or None."""
    try:
        data = _serializer().loads(token, max_age=TOKEN_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    member_id = data.get('member_id')
    if not member_id:
        return None
    return Member.query.get(member_id)


token_auth = HTTPTokenAuth(scheme='Bearer')


@token_auth.verify_token
def _verify(token):
    """APIFlask hook — return a truthy value (the Member) on success."""
    return verify_token_str(token)
