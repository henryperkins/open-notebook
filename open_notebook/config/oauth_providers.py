import os
from typing import Optional


def _get_redirect_base_url() -> str:
    """
    Determine the public base URL that should be used for OAuth callbacks.

    Priority:
    1. GOOGLE_REDIRECT_BASE_URL (explicit override for OAuth)
    2. API_URL (already recommended for browser-accessible base)
    3. NEXT_PUBLIC_APP_URL (used by some deployments)
    4. Default to localhost:8502 (matches docker-compose port and documentation)
    """
    for env_key in ("GOOGLE_REDIRECT_BASE_URL", "API_URL", "NEXT_PUBLIC_APP_URL"):
        value = os.environ.get(env_key)
        if value:
            return value.rstrip("/")
    return "http://localhost:8502"


def _build_redirect_uri(default_path: str, override_env_key: str) -> str:
    explicit: Optional[str] = os.environ.get(override_env_key)
    if explicit:
        return explicit
    base_url = _get_redirect_base_url()
    # Ensure we only have a single slash between base and path
    return f"{base_url.rstrip('/')}/{default_path.lstrip('/')}"


OAUTH_PROVIDERS = {
    "google": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        "redirect_uri": _build_redirect_uri(
            default_path="/api/oauth2/google/callback",
            override_env_key="GOOGLE_REDIRECT_URI",
        ),
    }
}
