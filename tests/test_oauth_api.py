"""
Basic tests for unified /api/oauth endpoints.
Covers: providers list, provider info, authorize flow, callback redirect.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def test_oauth_providers_list_includes_google_drive(client):
    res = client.get("/api/oauth/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    providers = {p["name"] for p in data["providers"]}
    assert "google_drive" in providers


def test_oauth_provider_info_not_connected(client):
    from api.services.oauth_service import oauth_service

    with patch.object(oauth_service, "get_user_tokens", new=AsyncMock(return_value=None)):
        res = client.get("/api/oauth/providers/google_drive/info")
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "google_drive"
        assert data["is_connected"] is False
        assert data["has_refresh_token"] is False


def test_oauth_authorize_success(client):
    from api.services.oauth_service import oauth_service, OAuthState

    # Seed state cache with a known state that our patched function will return
    oauth_service.state_cache.clear()
    oauth_service.state_cache["abc"] = OAuthState(
        state="abc",
        provider="google_drive",
        user_id="test-user",
    )

    with patch.object(
        oauth_service,
        "generate_authorization_url",
        new=AsyncMock(return_value=("http://example.com/auth", "abc")),
    ):
        res = client.post("/api/oauth/authorize", json={"provider": "google_drive"})
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "abc"
        assert data["authorization_url"].startswith("http://example.com")
        assert "expires_at" in data


def test_oauth_callback_success_redirect(client):
    from api.services.oauth_service import oauth_service, OAuthState, TokenResponse

    oauth_service.state_cache.clear()
    oauth_service.state_cache["st1"] = OAuthState(
        state="st1",
        provider="google_drive",
        user_id="u1",
        redirect_url="/settings",
    )

    with patch.object(
        oauth_service,
        "validate_webhook_callback",
        new=AsyncMock(return_value=(True, None)),
    ):
        with patch.object(
            oauth_service,
            "exchange_code_for_tokens",
            new=AsyncMock(return_value=TokenResponse(access_token="tok", token_type="Bearer")),
        ):
            res = client.get("/api/oauth/callback", params={"code": "code123", "state": "st1"})
            assert res.status_code == 302
            location = res.headers.get("location") or res.headers.get("Location")
            assert isinstance(location, str)
            assert location.startswith("/settings?")
            assert "provider=google_drive" in location
            assert "success=true" in location