import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.auth import UserInfo
from app.schemas.auth import AdminLoginRequest
from app.services.auth import (
    COOKIE_NAME,
    build_google_auth_url,
    create_jwt,
    decode_jwt,
    exchange_code_for_user,
    verify_admin_credentials,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)
settings = get_settings()

STATE_COOKIE = "oauth_state"

# Simple in-memory rate limiter for admin login: max 5 attempts per IP per 5 minutes
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 300  # seconds


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < _RATE_LIMIT_WINDOW]
    _login_attempts[ip] = attempts
    if len(attempts) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    _login_attempts[ip].append(now)


def _origin_from_request(request: Request) -> str:
    """Derive the public-facing origin (scheme + host) from the incoming request."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f"{forwarded_proto}://{host}"


@router.get("/login")
async def login(request: Request, response: Response) -> RedirectResponse:
    """Redirect browser to Google OAuth consent screen."""
    state = secrets.token_urlsafe(32)
    origin = _origin_from_request(request)
    url = build_google_auth_url(settings, state, origin=origin)
    redirect = RedirectResponse(url=url)
    # Store state in a short-lived cookie for CSRF protection
    redirect.set_cookie(
        STATE_COOKIE,
        state,
        max_age=300,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return redirect


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    """Handle Google OAuth callback, issue JWT, redirect to frontend."""
    if not oauth_state or state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    origin = _origin_from_request(request)

    try:
        user = await exchange_code_for_user(settings, code, origin=origin)
    except Exception as exc:
        logger.error("oauth_exchange_failed", error=str(exc))
        redirect = RedirectResponse(url=f"{origin}/login?error=oauth_failed")
        redirect.delete_cookie(STATE_COOKIE)
        return redirect

    # Enforce email domain restriction
    domain = user.email.split("@")[-1]
    if domain != settings.allowed_email_domain:
        logger.warning("oauth_domain_rejected", email=user.email, domain=domain)
        redirect = RedirectResponse(url=f"{origin}/login?error=domain_not_allowed")
        redirect.delete_cookie(STATE_COOKIE)
        return redirect

    token = create_jwt(settings, user)
    redirect = RedirectResponse(url=f"{origin}/")
    redirect.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    redirect.delete_cookie(STATE_COOKIE)
    logger.info("user_logged_in", email=user.email)
    return redirect


@router.post("/admin-login")
async def admin_login(body: AdminLoginRequest, request: Request, response: Response) -> UserInfo:
    """Password-based login for admin — bypasses Google OAuth."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    user = verify_admin_credentials(settings, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = create_jwt(settings, user)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    logger.info("admin_logged_in", email=user.email)
    return user


@router.get("/me", response_model=UserInfo)
async def me(ecc_token: str | None = Cookie(default=None)) -> UserInfo:
    """Return the currently authenticated user from the JWT cookie."""
    if not ecc_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = decode_jwt(settings, ecc_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return UserInfo(email=token_data.sub, name=token_data.name, picture=token_data.picture, is_admin=token_data.is_admin)


@router.post("/logout")
async def logout() -> Response:
    """Clear the JWT cookie."""
    response = Response(content='{"ok":true}', media_type="application/json")
    response.delete_cookie(COOKIE_NAME)
    return response
