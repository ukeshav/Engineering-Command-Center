from datetime import datetime, timedelta, timezone
UTC = timezone.utc

import httpx
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.auth import TokenData, UserInfo

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

ALGORITHM = "HS256"
COOKIE_NAME = "ecc_token"


def build_google_auth_url(settings: Settings, state: str, origin: str | None = None) -> str:
    base = (origin or settings.frontend_url).rstrip("/")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{base}/api/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_user(settings: Settings, code: str, origin: str | None = None) -> UserInfo:
    """Exchange OAuth code for Google user info."""
    base = (origin or settings.frontend_url).rstrip("/")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{base}/api/auth/callback",
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        data = userinfo_resp.json()

    return UserInfo(
        email=data["email"],
        name=data.get("name", data["email"]),
        picture=data.get("picture"),
    )


def create_jwt(settings: Settings, user: UserInfo) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": user.email,
        "name": user.name,
        "picture": user.picture,
        "is_admin": user.is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_jwt(settings: Settings, token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return TokenData(
            sub=payload["sub"],
            name=payload.get("name", payload["sub"]),
            picture=payload.get("picture"),
            is_admin=payload.get("is_admin", False),
        )
    except JWTError:
        return None


def verify_admin_credentials(settings: Settings, email: str, password: str) -> UserInfo | None:
    """Return admin UserInfo if credentials match config, else None."""
    if email == settings.admin_email and password == settings.admin_password:
        return UserInfo(email=email, name="Admin", picture=None, is_admin=True)
    return None
