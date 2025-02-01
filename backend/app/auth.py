import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

PASSWORD_ITERATIONS = 390_000
TOKEN_ALGORITHM = "HS256"
bearer_scheme = HTTPBearer(auto_error=False)


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False

    try:
        scheme, iterations, salt, expected = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64url_decode(salt),
            int(iterations),
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(_b64url_encode(digest), expected)


def create_access_token(*, subject: str, role: str) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iss": settings.TOKEN_ISSUER,
        "iat": issued_at,
        "exp": issued_at + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }
    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise _auth_error("Invalid access token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_b64url_encode(expected_signature), encoded_signature):
        raise _auth_error("Invalid access token")

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise _auth_error("Invalid access token") from exc

    if payload.get("iss") != settings.TOKEN_ISSUER:
        raise _auth_error("Invalid token issuer")

    if int(payload.get("exp", 0)) <= int(time.time()):
        raise _auth_error("Access token expired")

    return payload


def serialize_auth_user(user: User) -> dict:
    return {
        "id": user.id,
        "login_id": user.login_id,
        "role": user.role,
        "name": user.name,
        "zomato_partner_id": user.zomato_partner_id,
        "phone": user.phone,
        "zone": user.zone,
        "upi_handle": user.upi_handle,
        "base_urts": user.base_urts,
        "created_at": user.created_at,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _auth_error("Authentication required: missing bearer token")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise _auth_error("Invalid access token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise _auth_error("Account not found")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_rider_or_admin_access(rider_id: str, current_user: User) -> User:
    if current_user.role == "admin" or current_user.id == rider_id:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
