"""
OAuth 2.0 Service for secure third-party integrations with comprehensive token management,
security features, and support for multiple providers.
"""

import os
import json
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlencode, parse_qs
import httpx
from loguru import logger
from fastapi import HTTPException

from open_notebook.database.repository import repo_query, ensure_record_id


@dataclass
class OAuthProvider:
    """OAuth provider configuration with comprehensive settings."""
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: List[str]
    redirect_uri: str
    userinfo_url: Optional[str] = None
    revoke_url: Optional[str] = None
    pkce: bool = True  # Proof Key for Code Exchange
    state_length: int = 32


@dataclass
class TokenResponse:
    """OAuth token response with comprehensive metadata."""
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.expires_in and not self.expires_at:
            self.expires_at = self.created_at + timedelta(seconds=self.expires_in)
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def expires_soon(self, buffer_minutes: int = 5) -> bool:
        """Check if the token expires within the buffer time."""
        if not self.expires_at:
            return False
        buffer_time = timedelta(minutes=buffer_minutes)
        return datetime.now(timezone.utc) >= (self.expires_at - buffer_time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if data.get('created_at'):
            data['created_at'] = self.created_at.isoformat()
        if data.get('expires_at'):
            data['expires_at'] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenResponse':
        """Create from dictionary storage."""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


@dataclass
class OAuthState:
    """OAuth state for CSRF protection with metadata."""
    state: str
    provider: str
    user_id: str
    redirect_url: Optional[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=10)  # 10 minute expiry
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_expired(self) -> bool:
        """Check if the state is expired."""
        return datetime.now(timezone.utc) >= self.expires_at


class OAuthService:
    """Comprehensive OAuth 2.0 service with security, caching, and multi-provider support."""

    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self.state_cache: Dict[str, OAuthState] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._setup_default_providers()

    def _setup_default_providers(self):
        """Setup default OAuth providers with comprehensive configurations."""

        # Google Drive Provider
        self.providers['google_drive'] = OAuthProvider(
            name='google_drive',
            client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
            authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            userinfo_url='https://www.googleapis.com/oauth2/v2/userinfo',
            revoke_url='https://oauth2.googleapis.com/revoke',
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ],
            redirect_uri=os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8000/api/oauth/callback'),
            pkce=True
        )

        # Dropbox Provider (for future implementation)
        self.providers['dropbox'] = OAuthProvider(
            name='dropbox',
            client_id=os.getenv('DROPBOX_APP_KEY', ''),
            client_secret=os.getenv('DROPBOX_APP_SECRET', ''),
            authorize_url='https://www.dropbox.com/oauth2/authorize',
            token_url='https://api.dropboxapi.com/oauth2/token',
            scopes=['files.metadata.read', 'files.content.read'],
            redirect_uri=os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8000/api/oauth/callback'),
            pkce=False
        )

        # OneDrive Provider (for future implementation)
        self.providers['onedrive'] = OAuthProvider(
            name='onedrive',
            client_id=os.getenv('ONEDRIVE_CLIENT_ID', ''),
            client_secret=os.getenv('ONEDRIVE_CLIENT_SECRET', ''),
            authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
            scopes=['https://graph.microsoft.com/Files.Read', 'https://graph.microsoft.com/User.Read'],
            redirect_uri=os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8000/api/oauth/callback'),
            pkce=True
        )

    def get_provider(self, provider_name: str) -> OAuthProvider:
        """Get OAuth provider configuration."""
        provider = self.providers.get(provider_name)
        if not provider:
            raise HTTPException(status_code=404, detail=f"OAuth provider '{provider_name}' not found")
        return provider

    async def generate_authorization_url(
        self,
        provider_name: str,
        user_id: str,
        redirect_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL with PKCE and state management.

        Args:
            provider_name: Name of the OAuth provider
            user_id: User ID for the authorization request
            redirect_url: Optional URL to redirect after authorization
            metadata: Additional metadata to store with the state

        Returns:
            Tuple of (authorization_url, state)
        """
        provider = self.get_provider(provider_name)

        # Generate cryptographically secure state
        state = secrets.token_urlsafe(provider.state_length)

        # Create state object for CSRF protection
        oauth_state = OAuthState(
            state=state,
            provider=provider_name,
            user_id=user_id,
            redirect_url=redirect_url,
            metadata=metadata or {}
        )

        # Store state (in production, use Redis or database)
        self.state_cache[state] = oauth_state

        # Build authorization parameters
        auth_params = {
            'client_id': provider.client_id,
            'redirect_uri': provider.redirect_uri,
            'scope': ' '.join(provider.scopes),
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',  # For refresh tokens
            'prompt': 'consent',  # Force consent dialog for refresh tokens
        }

        # Add PKCE if supported
        code_verifier = None
        if provider.pkce:
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('utf-8')).digest()
            ).decode('utf-8').rstrip('=')

            auth_params['code_challenge'] = code_challenge
            auth_params['code_challenge_method'] = 'S256'

            # Store code verifier in state
            oauth_state.metadata['code_verifier'] = code_verifier

        # Build authorization URL
        auth_url = f"{provider.authorize_url}?{urlencode(auth_params)}"

        logger.info(f"Generated OAuth URL for {provider_name} with state {state[:8]}...")

        return auth_url, state

    async def exchange_code_for_tokens(
        self,
        provider_name: str,
        code: str,
        state: str
    ) -> TokenResponse:
        """
        Exchange authorization code for access tokens with comprehensive validation.

        Args:
            provider_name: Name of the OAuth provider
            code: Authorization code from the callback
            state: State parameter from the callback

        Returns:
            TokenResponse with access tokens and metadata
        """
        # Validate state
        oauth_state = self.state_cache.get(state)
        if not oauth_state:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        if oauth_state.is_expired:
            self.state_cache.pop(state, None)
            raise HTTPException(status_code=400, detail="State has expired")

        if oauth_state.provider != provider_name:
            raise HTTPException(status_code=400, detail="State provider mismatch")

        # Clean up state
        self.state_cache.pop(state, None)

        provider = self.get_provider(provider_name)

        # Prepare token request parameters
        token_data = {
            'client_id': provider.client_id,
            'client_secret': provider.client_secret,
            'code': code,
            'redirect_uri': provider.redirect_uri,
            'grant_type': 'authorization_code',
        }

        # Add PKCE verifier if used
        if provider.pkce and 'code_verifier' in oauth_state.metadata:
            token_data['code_verifier'] = oauth_state.metadata['code_verifier']

        try:
            # Exchange code for tokens
            response = await self.http_client.post(
                provider.token_url,
                data=token_data,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            response.raise_for_status()
            token_info = response.json()

            # Parse token response
            token_response = TokenResponse(
                access_token=token_info['access_token'],
                token_type=token_info.get('token_type', 'Bearer'),
                expires_in=token_info.get('expires_in'),
                refresh_token=token_info.get('refresh_token'),
                scope=token_info.get('scope'),
                metadata={
                    'provider': provider_name,
                    'user_id': oauth_state.user_id,
                    'granted_scopes': token_info.get('scope', '').split(' ') if token_info.get('scope') else [],
                    'original_response': token_info
                }
            )

            # Store tokens securely
            await self.store_user_tokens(oauth_state.user_id, provider_name, token_response)

            logger.info(f"Successfully exchanged tokens for {provider_name} user {oauth_state.user_id}")

            return token_response

        except httpx.HTTPStatusError as e:
            logger.error(f"Token exchange failed for {provider_name}: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Token exchange failed: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {str(e)}")
            raise HTTPException(status_code=500, detail="Token exchange failed")

    async def refresh_access_token(
        self,
        provider_name: str,
        user_id: str
    ) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token.

        Args:
            provider_name: Name of the OAuth provider
            user_id: User ID

        Returns:
            New TokenResponse or None if refresh failed
        """
        try:
            # Get stored tokens
            stored_tokens = await self.get_user_tokens(user_id, provider_name)
            if not stored_tokens or not stored_tokens.refresh_token:
                logger.warning(f"No refresh token available for {provider_name} user {user_id}")
                return None

            provider = self.get_provider(provider_name)

            # Prepare refresh request
            refresh_data = {
                'client_id': provider.client_id,
                'client_secret': provider.client_secret,
                'refresh_token': stored_tokens.refresh_token,
                'grant_type': 'refresh_token',
            }

            # Refresh the token
            response = await self.http_client.post(
                provider.token_url,
                data=refresh_data,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            response.raise_for_status()
            token_info = response.json()

            # Create new token response
            new_tokens = TokenResponse(
                access_token=token_info['access_token'],
                token_type=token_info.get('token_type', 'Bearer'),
                expires_in=token_info.get('expires_in'),
                refresh_token=token_info.get('refresh_token') or stored_tokens.refresh_token,
                scope=token_info.get('scope') or stored_tokens.scope,
                metadata={
                    **stored_tokens.metadata,
                    'refreshed_at': datetime.now(timezone.utc).isoformat(),
                    'original_response': token_info
                }
            )

            # Store new tokens
            await self.store_user_tokens(user_id, provider_name, new_tokens)

            logger.info(f"Successfully refreshed tokens for {provider_name} user {user_id}")

            return new_tokens

        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh failed for {provider_name} user {user_id}: {e.response.text}")
            # If refresh fails, tokens might be revoked - clean them up
            await self.delete_user_tokens(user_id, provider_name)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            return None

    async def get_valid_access_token(
        self,
        provider_name: str,
        user_id: str
    ) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary.

        Args:
            provider_name: Name of the OAuth provider
            user_id: User ID

        Returns:
            Valid access token or None if unavailable
        """
        tokens = await self.get_user_tokens(user_id, provider_name)
        if not tokens:
            return None

        # Check if token needs refresh
        if tokens.is_expired or tokens.expires_soon():
            logger.info(f"Token expired for {provider_name} user {user_id}, attempting refresh")
            new_tokens = await self.refresh_access_token(provider_name, user_id)
            return new_tokens.access_token if new_tokens else None

        return tokens.access_token

    async def store_user_tokens(
        self,
        user_id: str,
        provider_name: str,
        tokens: TokenResponse
    ) -> None:
        """
        Store user tokens securely in the database.

        Args:
            user_id: User ID
            provider_name: OAuth provider name
            tokens: Token response to store
        """
        try:
            # Store in database using existing repository pattern
            token_data = {
                'user_id': user_id,
                'provider': provider_name,
                'access_token': tokens.access_token,
                'token_type': tokens.token_type,
                'refresh_token': tokens.refresh_token,
                'scope': tokens.scope,
                'expires_at': tokens.expires_at.isoformat() if tokens.expires_at else None,
                'metadata': json.dumps(tokens.metadata),
                'created_at': tokens.created_at.isoformat()
            }

            # Check if tokens already exist for this user/provider
            existing = await repo_query(
                "SELECT * FROM oauth_tokens WHERE user_id = $user_id AND provider = $provider",
                {"user_id": user_id, "provider": provider_name}
            )

            if existing:
                # Update existing tokens
                await repo_query(
                    """
                    UPDATE oauth_tokens SET
                        access_token = $access_token,
                        token_type = $token_type,
                        refresh_token = $refresh_token,
                        scope = $scope,
                        expires_at = $expires_at,
                        metadata = $metadata,
                        updated_at = time::now()
                    WHERE user_id = $user_id AND provider = $provider
                    """,
                    token_data
                )
            else:
                # Insert new tokens
                await repo_query(
                    """
                    INSERT INTO oauth_tokens (
                        user_id, provider, access_token, token_type,
                        refresh_token, scope, expires_at, metadata,
                        created_at, updated_at
                    ) VALUES (
                        $user_id, $provider, $access_token, $token_type,
                        $refresh_token, $scope, $expires_at, $metadata,
                        time::now(), time::now()
                    )
                    """,
                    token_data
                )

            logger.info(f"Stored tokens for {provider_name} user {user_id}")

        except Exception as e:
            logger.error(f"Failed to store tokens for {provider_name} user {user_id}: {str(e)}")
            raise

    async def get_user_tokens(
        self,
        user_id: str,
        provider_name: str
    ) -> Optional[TokenResponse]:
        """
        Retrieve user tokens from the database.

        Args:
            user_id: User ID
            provider_name: OAuth provider name

        Returns:
            TokenResponse or None if not found
        """
        try:
            result = await repo_query(
                "SELECT * FROM oauth_tokens WHERE user_id = $user_id AND provider = $provider",
                {"user_id": user_id, "provider": provider_name}
            )

            if not result or len(result) == 0:
                return None

            token_data = result[0]
            return TokenResponse(
                access_token=token_data['access_token'],
                token_type=token_data['token_type'],
                refresh_token=token_data['refresh_token'],
                scope=token_data['scope'],
                expires_at=datetime.fromisoformat(token_data['expires_at']) if token_data['expires_at'] else None,
                metadata=json.loads(token_data['metadata']) if token_data['metadata'] else {}
            )

        except Exception as e:
            logger.error(f"Failed to retrieve tokens for {provider_name} user {user_id}: {str(e)}")
            return None

    async def delete_user_tokens(
        self,
        user_id: str,
        provider_name: str
    ) -> bool:
        """
        Delete user tokens from the database.

        Args:
            user_id: User ID
            provider_name: OAuth provider name

        Returns:
            True if successful, False otherwise
        """
        try:
            await repo_query(
                "DELETE FROM oauth_tokens WHERE user_id = $user_id AND provider = $provider",
                {"user_id": user_id, "provider": provider_name}
            )

            logger.info(f"Deleted tokens for {provider_name} user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete tokens for {provider_name} user {user_id}: {str(e)}")
            return False

    async def revoke_tokens(
        self,
        provider_name: str,
        user_id: str
    ) -> bool:
        """
        Revoke tokens with the provider and delete from database.

        Args:
            provider_name: OAuth provider name
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            tokens = await self.get_user_tokens(user_id, provider_name)
            if not tokens:
                return False

            provider = self.get_provider(provider_name)

            # Revoke with provider if revoke URL is available
            if provider.revoke_url:
                try:
                    await self.http_client.post(
                        provider.revoke_url,
                        data={'token': tokens.access_token},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                    logger.info(f"Successfully revoked token with {provider_name}")
                except Exception as e:
                    logger.warning(f"Failed to revoke token with {provider_name}: {str(e)}")

            # Delete from database
            await self.delete_user_tokens(user_id, provider_name)

            return True

        except Exception as e:
            logger.error(f"Failed to revoke tokens for {provider_name} user {user_id}: {str(e)}")
            return False

    async def validate_webhook_callback(
        self,
        provider_name: str,
        state: str,
        code: str,
        error: Optional[str] = None,
        error_description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate OAuth callback and handle errors.

        Args:
            provider_name: OAuth provider name
            state: State parameter from callback
            code: Authorization code from callback
            error: Error parameter from callback
            error_description: Error description from callback

        Returns:
            Tuple of (is_valid, error_message)
        """
        if error:
            error_msg = error_description or f"OAuth error: {error}"
            logger.error(f"OAuth callback error for {provider_name}: {error_msg}")
            return False, error_msg

        if not code:
            return False, "No authorization code received"

        # Validate state
        oauth_state = self.state_cache.get(state)
        if not oauth_state:
            return False, "Invalid or expired state"

        if oauth_state.is_expired:
            self.state_cache.pop(state, None)
            return False, "State has expired"

        if oauth_state.provider != provider_name:
            return False, "State provider mismatch"

        return True, None

    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired OAuth states.

        Returns:
            Number of states cleaned up
        """
        current_time = datetime.now(timezone.utc)
        expired_states = [
            state for state, oauth_state in self.state_cache.items()
            if oauth_state.expires_at <= current_time
        ]

        for state in expired_states:
            self.state_cache.pop(state, None)

        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")

        return len(expired_states)

    async def get_user_integrations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all OAuth integrations for a user.

        Args:
            user_id: User ID

        Returns:
            List of integration information
        """
        try:
            result = await repo_query(
                """
                SELECT provider, created_at, updated_at, scope, metadata
                FROM oauth_tokens
                WHERE user_id = $user_id
                ORDER BY created_at DESC
                """,
                {"user_id": user_id}
            )

            integrations = []
            for token_data in result or []:
                provider_name = token_data['provider']
                provider = self.get_provider(provider_name)

                integrations.append({
                    'provider': provider_name,
                    'display_name': provider.name.replace('_', ' ').title(),
                    'scopes': token_data['scope'].split(' ') if token_data['scope'] else [],
                    'created_at': token_data['created_at'],
                    'updated_at': token_data['updated_at'],
                    'has_refresh_token': bool(token_data['refresh_token']),
                    'metadata': json.loads(token_data['metadata']) if token_data['metadata'] else {}
                })

            return integrations

        except Exception as e:
            logger.error(f"Failed to get integrations for user {user_id}: {str(e)}")
            return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()


# Global OAuth service instance
oauth_service = OAuthService()
