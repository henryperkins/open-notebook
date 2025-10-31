"""
OAuth API endpoints for secure third-party service integrations with comprehensive
authentication flow management and error handling.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import RedirectResponse
from loguru import logger
import secrets
import os

from api.services.oauth_service import oauth_service, OAuthState
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/oauth", tags=["oauth"])


async def get_current_user(request: Request) -> Dict[str, str]:
    """
    Get the current authenticated user.

    When password auth is enabled, creates a session-based user identifier.
    When password auth is disabled, uses a consistent anonymous identifier.
    """
    # Check if password auth is enabled
    password_enabled = bool(os.environ.get("OPEN_NOTEBOOK_PASSWORD"))

    if password_enabled:
        # For password-protected instances, use session-based identification
        if "user_id" not in request.session:
            # Create a unique user ID for this session
            request.session["user_id"] = f"session-{secrets.token_urlsafe(16)}"
            request.session["created_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "id": request.session["user_id"],
            "username": f"user-{request.session['user_id'][:8]}",
            "authenticated": True
        }
    else:
        # For non-password instances, create a consistent anonymous user
        # This allows OAuth to work while maintaining isolation
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Create a consistent but anonymous identifier
        import hashlib
        identifier = f"{client_ip}:{hashlib.sha256(user_agent.encode()).hexdigest()[:16]}"

        return {
            "id": f"anon-{hashlib.sha256(identifier.encode()).hexdigest()[:16]}",
            "username": "anonymous",
            "authenticated": False
        }


# Request/Response Models
class OAuthAuthorizeRequest(BaseModel):
    """Request model for OAuth authorization initiation."""
    provider: str = Field(..., description="OAuth provider name")
    redirect_url: Optional[str] = Field(None, description="URL to redirect after authorization")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class OAuthAuthorizeResponse(BaseModel):
    """Response model for OAuth authorization initiation."""
    authorization_url: str
    state: str
    expires_at: datetime


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback processing."""
    success: bool
    provider: str
    access_token: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrationInfo(BaseModel):
    """Integration information model."""
    provider: str
    display_name: str
    scopes: List[str]
    created_at: datetime
    updated_at: datetime
    has_refresh_token: bool
    metadata: Dict[str, Any]


@router.post("/authorize", response_model=OAuthAuthorizeResponse)
async def initiate_oauth_authorization(
    api_request: Request,
    request: OAuthAuthorizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate OAuth authorization flow for a third-party service.

    Args:
        request: OAuth authorization request
        current_user: Authenticated user

    Returns:
        Authorization URL and state for CSRF protection

    Raises:
        HTTPException: For invalid requests or provider not found
    """
    try:
        user_id = current_user.get("id", "anonymous")

        # Generate authorization URL and state
        auth_url, state = await oauth_service.generate_authorization_url(
            provider_name=request.provider,
            user_id=user_id,
            redirect_url=request.redirect_url,
            metadata=request.metadata or {}
        )

        # Get state object for expiry time
        oauth_state = oauth_service.state_cache.get(state)
        if not oauth_state:
            raise HTTPException(status_code=500, detail="Failed to generate OAuth state")

        logger.info(f"Initiated OAuth authorization for {request.provider} user {user_id}")

        return OAuthAuthorizeResponse(
            authorization_url=auth_url,
            state=state,
            expires_at=oauth_state.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate OAuth authorization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate OAuth authorization: {str(e)}"
        )


@router.get("/callback")
async def handle_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    error: Optional[str] = Query(None, description="Error parameter"),
    error_description: Optional[str] = Query(None, description="Error description")
):
    """
    Handle OAuth callback from third-party service.

    Args:
        request: FastAPI request object
        code: Authorization code
        state: State parameter
        error: Error parameter (if any)
        error_description: Error description (if any)

    Returns:
        Redirect response or error information
    """
    try:
        # Get state information
        oauth_state = oauth_service.state_cache.get(state)
        if not oauth_state:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        # Validate callback
        is_valid, error_msg = await oauth_service.validate_webhook_callback(
            provider_name=oauth_state.provider,
            state=state,
            code=code,
            error=error,
            error_description=error_description
        )

        if not is_valid:
            logger.error(f"OAuth callback validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Exchange code for tokens
        token_response = await oauth_service.exchange_code_for_tokens(
            provider_name=oauth_state.provider,
            code=code,
            state=state
        )

        # Determine redirect URL
        redirect_url = oauth_state.redirect_url or "/integrations/success"

        # Add success information to redirect URL
        success_params = {
            "provider": oauth_state.provider,
            "success": "true"
        }

        separator = "&" if "?" in redirect_url else "?"
        full_redirect_url = f"{redirect_url}{separator}{urlencode(success_params)}"

        logger.info(f"Successfully completed OAuth flow for {oauth_state.provider} user {oauth_state.user_id}")

        return RedirectResponse(url=full_redirect_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {str(e)}")

        # Get state for error handling
        oauth_state = oauth_service.state_cache.get(state)
        error_redirect = "/integrations/error"

        if oauth_state and oauth_state.redirect_url:
            error_redirect = oauth_state.redirect_url

        error_params = {
            "error": "oauth_failed",
            "message": str(e)
        }

        separator = "&" if "?" in error_redirect else "?"
        error_url = f"{error_redirect}{separator}{urlencode(error_params)}"

        return RedirectResponse(url=error_url, status_code=302)


@router.get("/integrations")
async def get_user_integrations(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> List[IntegrationInfo]:
    """
    Get all OAuth integrations for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of user's OAuth integrations
    """
    try:
        user_id = current_user.get("id", "anonymous")

        integrations = await oauth_service.get_user_integrations(user_id)

        return [
            IntegrationInfo(
                provider=integration['provider'],
                display_name=integration['display_name'],
                scopes=integration['scopes'],
                created_at=datetime.fromisoformat(integration['created_at']),
                updated_at=datetime.fromisoformat(integration['updated_at']),
                has_refresh_token=integration['has_refresh_token'],
                metadata=integration['metadata']
            )
            for integration in integrations
        ]

    except Exception as e:
        logger.error(f"Failed to get user integrations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user integrations"
        )


@router.delete("/integrations/{provider}")
async def revoke_integration(
    request: Request,
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Revoke OAuth integration and delete stored tokens.

    Args:
        provider: OAuth provider name
        current_user: Authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: For provider not found or revocation failure
    """
    try:
        user_id = current_user.get("id", "anonymous")

        # Check if provider exists
        oauth_service.get_provider(provider)

        # Revoke tokens
        success = await oauth_service.revoke_tokens(provider, user_id)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to revoke {provider} integration"
            )

        logger.info(f"Successfully revoked {provider} integration for user {user_id}")

        return {
            "success": True,
            "message": f"{provider.replace('_', ' ').title()} integration has been revoked successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke integration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke {provider} integration: {str(e)}"
        )


@router.post("/integrations/{provider}/refresh")
async def refresh_integration(
    request: Request,
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually refresh OAuth tokens for an integration.

    Args:
        provider: OAuth provider name
        current_user: Authenticated user

    Returns:
        Success message with token information

    Raises:
        HTTPException: For provider not found or refresh failure
    """
    try:
        user_id = current_user.get("id", "anonymous")

        # Check if provider exists
        oauth_service.get_provider(provider)

        # Refresh tokens
        new_tokens = await oauth_service.refresh_access_token(provider, user_id)

        if not new_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to refresh {provider} tokens. Please re-authorize."
            )

        logger.info(f"Successfully refreshed {provider} tokens for user {user_id}")

        return {
            "success": True,
            "message": f"{provider.replace('_', ' ').title()} tokens refreshed successfully",
            "expires_at": new_tokens.expires_at.isoformat() if new_tokens.expires_at else None,
            "has_refresh_token": bool(new_tokens.refresh_token)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh integration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh {provider} tokens: {str(e)}"
        )


@router.get("/providers")
async def get_available_providers():
    """
    Get list of available OAuth providers.

    Returns:
        List of available providers with configuration info
    """
    try:
        providers = []

        for provider_name, provider_config in oauth_service.providers.items():
            providers.append({
                "name": provider_name,
                "display_name": provider_config.name.replace('_', ' ').title(),
                "scopes": provider_config.scopes,
                "supports_pkce": provider_config.pkce,
                "requires_client_secret": bool(provider_config.client_secret)
            })

        return {"providers": providers}

    except Exception as e:
        logger.error(f"Failed to get available providers: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve available providers"
        )


@router.get("/providers/{provider}/info")
async def get_provider_info(
    request: Request,
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific OAuth provider.

    Args:
        provider: OAuth provider name
        current_user: Authenticated user

    Returns:
        Provider information and user's integration status
    """
    try:
        user_id = current_user.get("id", "anonymous")

        # Get provider configuration
        provider_config = oauth_service.get_provider(provider)

        # Check if user has active integration
        user_tokens = await oauth_service.get_user_tokens(user_id, provider)
        is_connected = bool(user_tokens)

        result = {
            "provider": provider,
            "display_name": provider_config.name.replace('_', ' ').title(),
            "scopes": provider_config.scopes,
            "supports_pkce": provider_config.pkce,
            "is_connected": is_connected,
            "has_refresh_token": bool(user_tokens.refresh_token) if user_tokens else False,
            "connected_at": user_tokens.created_at.isoformat() if user_tokens else None,
            "expires_at": user_tokens.expires_at.isoformat() if user_tokens and user_tokens.expires_at else None,
            "is_expired": user_tokens.is_expired if user_tokens else False,
            "expires_soon": user_tokens.expires_soon() if user_tokens else False
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve provider information: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_expired_states():
    """
    Clean up expired OAuth states (maintenance endpoint).

    Returns:
        Number of cleaned up states
    """
    try:
        cleaned_count = await oauth_service.cleanup_expired_states()

        return {
            "success": True,
            "cleaned_states": cleaned_count,
            "message": f"Cleaned up {cleaned_count} expired OAuth states"
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired states: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup expired states"
        )


# Helper function for URL encoding
def urlencode(params: Dict[str, Any]) -> str:
    """URL encode parameters."""
    from urllib.parse import urlencode
    return urlencode(params)