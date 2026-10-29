"""
API key check (the API_KEY of config.yaml's course template, now really used).

Writes on the catalogue (POST/PUT/DELETE /books) need the header
X-API-Key = API_KEY of the environment. Each environment has its OWN key:
a staging key does not work in prod. In Unit 04 this check moves to the gateway.
"""
import hmac

from fastapi import Header, HTTPException

from .settings import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # compare_digest: constant-time comparison (no timing attack on the key)
    if x_api_key is None or not hmac.compare_digest(x_api_key, get_settings().API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid API key",
                            headers={"WWW-Authenticate": "ApiKey"})
