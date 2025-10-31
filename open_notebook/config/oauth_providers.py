import os
from typing import Optional


def _get_redirect_base_url() -> str:
    """
    Determine the public base URL that should be used for OAuth callbacks.

    Priority:
    1. OAUTH_REDIRECT_BASE_URL (global override for OAuth callbacks)
    2. GOOGLE_REDIRECT_BASE_URL (provider-specific legacy override)
    3. API_URL (already recommended for browser-accessible base)
    4. NEXT_PUBLIC_APP_URL (used by some deployments)
    5. Derived from API_* env vars (defaults to http://localhost:5055)
    """
    for env_key in (
        "OAUTH_REDIRECT_BASE_URL",
        "GOOGLE_REDIRECT_BASE_URL",
        "API_URL",
        "NEXT_PUBLIC_APP_URL",
    ):
        value = os.environ.get(env_key)
        if value:
            return value.rstrip("/")

    host = os.environ.get("API_HOST", "127.0.0.1")
    if host in {"0.0.0.0", "::"}:
        host = "localhost"
    port = os.environ.get("API_PORT", "5055")
    scheme = os.environ.get("API_SCHEME", "http")
    return f"{scheme}://{host}:{port}".rstrip("/")


def _build_redirect_uri(
    default_path: str,
    override_env_keys: tuple[str, ...],
) -> str:
    for env_key in override_env_keys:
        explicit: Optional[str] = os.environ.get(env_key)
        if explicit:
            return explicit
    base_url = _get_redirect_base_url()
    # Ensure we only have a single slash between base and path
    return f"{base_url.rstrip('/')}/{default_path.lstrip('/')}"


def get_oauth_redirect_uri(
    default_path: str = "/api/oauth/callback",
    override_env_keys: Optional[tuple[str, ...]] = None,
) -> str:
    """
    Public helper to resolve the OAuth redirect URI consistently across services.
    """
    keys = override_env_keys or ("OAUTH_REDIRECT_URI",)
    return _build_redirect_uri(default_path, keys)


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
            default_path="/api/oauth/callback",
            override_env_keys=("GOOGLE_REDIRECT_URI", "OAUTH_REDIRECT_URI"),
        ),
    }
}
