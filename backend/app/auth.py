from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


async def require_auth(authorization: str | None = Header(default=None)) -> None:
    if settings.app_env == "development":
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.app_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
