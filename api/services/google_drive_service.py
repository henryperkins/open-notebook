"""
Google Drive Service with comprehensive file management, search capabilities,
and intelligent caching for optimal performance.
"""

import json
import mimetypes
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urlencode

import httpx
from fastapi import HTTPException
from loguru import logger

from api.sources_service import SourceProcessingResult, create_source
from open_notebook.domain.notebook import Source

from .oauth_service import oauth_service


@dataclass
class GoogleDriveFile:
    """Google Drive file representation with comprehensive metadata."""
    id: str
    name: str
    mime_type: str
    size: int
    created_time: datetime
    modified_time: datetime
    parents: List[str]
    web_view_link: str
    web_content_link: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_folder(self) -> bool:
        """Check if file is a folder."""
        return self.mime_type == 'application/vnd.google-apps.folder'

    @property
    def is_document(self) -> bool:
        """Check if file is a Google Document."""
        return self.mime_type == 'application/vnd.google-apps.document'

    @property
    def is_spreadsheet(self) -> bool:
        """Check if file is a Google Sheet."""
        return self.mime_type == 'application/vnd.google-apps.spreadsheet'

    @property
    def is_slides(self) -> bool:
        """Check if file is a Google Slides presentation."""
        return self.mime_type == 'application/vnd.google-apps.presentation'

    @property
    def is_pdf(self) -> bool:
        """Check if file is a PDF."""
        return self.mime_type == 'application/pdf'

    @property
    def is_supported_for_download(self) -> bool:
        """Check if file can be downloaded for processing."""
        return (
            not self.is_folder
            and (bool(self.web_content_link) or not self.is_document)
        )

    @property
    def display_name(self) -> str:
        """Get display name with extension for Google Workspace files."""
        if self.is_document:
            return f"{self.name}.gdoc"
        elif self.is_spreadsheet:
            return f"{self.name}.gsheet"
        elif self.is_slides:
            return f"{self.name}.gslides"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if data.get('created_time'):
            data['created_time'] = self.created_time.isoformat()
        if data.get('modified_time'):
            data['modified_time'] = self.modified_time.isoformat()
        return data

    @classmethod
    def from_api_response(cls, file_data: Dict[str, Any]) -> 'GoogleDriveFile':
        """Create from Google Drive API response."""
        return cls(
            id=file_data['id'],
            name=file_data['name'],
            mime_type=file_data['mimeType'],
            size=int(file_data.get('size', 0)),
            created_time=datetime.fromisoformat(file_data['createdTime'].replace('Z', '+00:00')),
            modified_time=datetime.fromisoformat(file_data['modifiedTime'].replace('Z', '+00:00')),
            parents=file_data.get('parents', []),
            web_view_link=file_data.get('webViewLink', ''),
            web_content_link=file_data.get('webContentLink'),
            metadata={
                'capabilities': file_data.get('capabilities', {}),
                'permissions': file_data.get('permissions', []),
                'owners': file_data.get('owners', []),
                'shared': file_data.get('shared', False),
                'trashed': file_data.get('trashed', False)
            }
        )


@dataclass
class SearchQuery:
    """Search query builder for Google Drive files."""
    query: str = ""
    mime_types: List[str] = field(default_factory=list)
    folder_id: Optional[str] = None
    file_size_min: Optional[int] = None
    file_size_max: Optional[int] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    trashed: bool = False
    order_by: str = "modifiedTime desc"
    page_size: int = 100

    def build_query(self) -> str:
        """Build Google Drive query string."""
        conditions = []

        if self.query:
            # Full-text search
            escaped_query = self.query.replace("'", "\\'")
            conditions.append(f"fullText contains '{escaped_query}'")

        if self.mime_types:
            mime_conditions = [f"mimeType = '{mime}'" for mime in self.mime_types]
            conditions.append(f"({' or '.join(mime_conditions)})")

        if self.folder_id:
            conditions.append(f"'{self.folder_id}' in parents")

        if self.file_size_min is not None:
            conditions.append(f"size > {self.file_size_min}")

        if self.file_size_max is not None:
            conditions.append(f"size < {self.file_size_max}")

        if self.modified_after:
            timestamp = self.modified_after.isoformat().replace('+00:00', 'Z')
            conditions.append(f"modifiedTime > '{timestamp}'")

        if self.modified_before:
            timestamp = self.modified_before.isoformat().replace('+00:00', 'Z')
            conditions.append(f"modifiedTime < '{timestamp}'")

        if not self.trashed:
            conditions.append("trashed = false")

        return " and ".join(conditions)


class GoogleDriveService:
    """Comprehensive Google Drive service with intelligent caching and error handling."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(minutes=15)

    def _cache_key(self, user_id: str, operation: str, **kwargs) -> str:
        """Generate cache key for operations."""
        key_parts = [user_id, operation] + [f"{k}:{v}" for k, v in sorted(kwargs.items())]
        return ":".join(key_parts)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now(timezone.utc) - timestamp < self.cache_ttl:
                return data
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Set value in cache with timestamp."""
        self.cache[key] = (value, datetime.now(timezone.utc))

    async def _make_api_request(
        self,
        user_id: str,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Union[Dict[str, Any], bytes]:
        """
        Make authenticated API request to Google Drive.

        Args:
            user_id: User ID for authentication
            url: API URL
            method: HTTP method
            **kwargs: Additional arguments for httpx

        Returns:
            API response data
        """
        # Get valid access token
        access_token = await oauth_service.get_valid_access_token('google_drive', user_id)
        if not access_token:
            raise HTTPException(status_code=401, detail="Google Drive access token not available")

        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'

        try:
            response = await self.http_client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()

            # Handle different response formats
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return response.json()
            return response.content

        except httpx.HTTPStatusError as e:
            logger.error(f"Google Drive API error: {e.response.status_code} - {e.response.text}")

            # Handle token expiration
            if e.response.status_code == 401:
                # Try to refresh token and retry once
                new_token = await oauth_service.refresh_access_token('google_drive', user_id)
                if new_token:
                    headers['Authorization'] = f'Bearer {new_token.access_token}'
                    response = await self.http_client.request(method, url, headers=headers, **kwargs)
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        return response.json()
                    return response.content

            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Google Drive API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in Google Drive API request: {str(e)}")
            raise HTTPException(status_code=500, detail="Google Drive service error")

    async def list_files(
        self,
        user_id: str,
        query: SearchQuery,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List files from Google Drive with comprehensive search capabilities.

        Args:
            user_id: User ID
            query: Search query parameters
            page_token: Pagination token

        Returns:
            Dictionary with files and pagination info
        """
        # Check cache first
        cache_key = self._cache_key(user_id, 'list_files', **asdict(query), page_token=page_token)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        base_url = "https://www.googleapis.com/drive/v3/files"
        params = {
            'q': query.build_query(),
            'orderBy': query.order_by,
            'pageSize': query.page_size,
            'fields': 'nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, capabilities, permissions, owners, shared, trashed)',
            'includeItemsFromAllDrives': False,
            'supportsAllDrives': True
        }

        if page_token:
            params['pageToken'] = page_token

        url = f"{base_url}?{urlencode(params)}"

        try:
            response = await self._make_api_request(user_id, url)

            if not isinstance(response, dict):
                raise HTTPException(status_code=500, detail="Unexpected response format from Google Drive")

            # Convert API response to our format
            files = [GoogleDriveFile.from_api_response(file_data) for file_data in response.get('files', [])]

            result = {
                'files': [file.to_dict() for file in files],
                'next_page_token': response.get('nextPageToken'),
                'total_items': len(files),
                'has_more': bool(response.get('nextPageToken'))
            }

            # Cache the result
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to list files for user {user_id}: {str(e)}")
            raise

    async def get_file_metadata(self, user_id: str, file_id: str) -> GoogleDriveFile:
        """
        Get detailed metadata for a specific file.

        Args:
            user_id: User ID
            file_id: Google Drive file ID

        Returns:
            GoogleDriveFile object
        """
        # Check cache first
        cache_key = self._cache_key(user_id, 'file_metadata', file_id=file_id)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return GoogleDriveFile.from_api_response(cached_result)

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {
            'fields': 'id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, capabilities, permissions, owners, shared, trashed',
            'supportsAllDrives': True
        }

        full_url = f"{url}?{urlencode(params)}"

        try:
            response = await self._make_api_request(user_id, full_url)

            if not isinstance(response, dict):
                raise HTTPException(status_code=500, detail="Unexpected metadata response from Google Drive")

            # Cache the result
            self._set_cache(cache_key, response)

            return GoogleDriveFile.from_api_response(response)

        except Exception as e:
            logger.error(f"Failed to get file metadata for {file_id}: {str(e)}")
            raise

    async def download_file(self, user_id: str, file_id: str) -> bytes:
        """
        Download file content from Google Drive.

        Args:
            user_id: User ID
            file_id: Google Drive file ID

        Returns:
            File content as bytes
        """
        # Get file metadata first
        file_info = await self.get_file_metadata(user_id, file_id)

        if file_info.is_folder:
            raise HTTPException(status_code=400, detail="Cannot download folders")

        # Handle Google Workspace files
        if file_info.is_document or file_info.is_spreadsheet or file_info.is_slides:
            return await self._export_google_workspace_file(user_id, file_id, file_info.mime_type)

        # Regular file download
        if not file_info.web_content_link:
            raise HTTPException(status_code=400, detail="File cannot be downloaded")

        try:
            response = await self._make_api_request(user_id, file_info.web_content_link)

            if isinstance(response, bytes):
                return response

            raise HTTPException(status_code=500, detail="Unexpected response when downloading file")

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to download file")

    async def _export_google_workspace_file(
        self,
        user_id: str,
        file_id: str,
        mime_type: str
    ) -> bytes:
        """
        Export Google Workspace file to appropriate format.

        Args:
            user_id: User ID
            file_id: File ID
            mime_type: Original MIME type

        Returns:
            Exported file content as bytes
        """
        # Map Google Workspace MIME types to export formats
        export_formats = {
            'application/vnd.google-apps.document': 'application/pdf',
            'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.drawing': 'image/png',
            'application/vnd.google-apps.script': 'application/vnd.google-apps.script+json',
        }

        export_mime = export_formats.get(mime_type, 'application/pdf')

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        params = {'mimeType': export_mime}
        full_url = f"{url}?{urlencode(params)}"

        try:
            response = await self._make_api_request(user_id, full_url)

            if isinstance(response, bytes):
                return response

            raise HTTPException(status_code=500, detail="Unexpected export response from Google Drive")

        except Exception as e:
            logger.error(f"Failed to export Google Workspace file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to export file")

    async def search_files(
        self,
        user_id: str,
        query: str = "",
        mime_types: Optional[List[str]] = None,
        folder_id: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search files with advanced filtering.

        Args:
            user_id: User ID
            query: Search query string
            mime_types: List of MIME types to filter
            folder_id: Folder ID to search within
            page_size: Number of results per page
            page_token: Pagination token

        Returns:
            Search results with files and pagination
        """
        search_query = SearchQuery(
            query=query,
            mime_types=mime_types or [],
            folder_id=folder_id,
            page_size=page_size
        )

        return await self.list_files(user_id, search_query, page_token)

    async def get_folder_contents(
        self,
        user_id: str,
        folder_id: str,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get contents of a specific folder.

        Args:
            user_id: User ID
            folder_id: Folder ID
            page_size: Number of results per page

        Returns:
            Folder contents
        """
        query = SearchQuery(
            folder_id=folder_id,
            page_size=page_size,
            order_by="name asc"
        )

        return await self.list_files(user_id, query)

    async def get_root_folder_contents(
        self,
        user_id: str,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get contents of root folder.

        Args:
            user_id: User ID
            page_size: Number of results per page

        Returns:
            Root folder contents
        """
        query = SearchQuery(
            query="'root' in parents",
            page_size=page_size,
            order_by="name asc"
        )

        return await self.list_files(user_id, query)

    async def sync_file_to_source(
        self,
        user_id: str,
        file_id: str,
        notebook_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sync Google Drive file to notebook source.

        Args:
            user_id: User ID
            file_id: Google Drive file ID
            notebook_ids: List of notebook IDs to assign to

        Returns:
            Created source information
        """
        if not notebook_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one notebook ID is required to sync Google Drive files",
            )

        # Get file metadata
        file_info = await self.get_file_metadata(user_id, file_id)

        if not file_info.is_supported_for_download:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_info.mime_type} is not supported for sync"
            )

        # Download file content
        file_content = await self.download_file(user_id, file_id)

        # Create source using existing source creation logic
        source_data = {
            "title": file_info.name,
            "type": "upload",
            "notebooks": notebook_ids or [],
            "delete_source": True,
            "async_processing": True,
            "source_metadata": {
                "provider": "google_drive",
                "file_id": file_id,
                "original_mime_type": file_info.mime_type,
                "web_view_link": file_info.web_view_link,
                "size": file_info.size,
                "modified_time": file_info.modified_time.isoformat(),
                "google_drive_metadata": file_info.metadata
            }
        }

        # Create a temporary file for the upload
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(file_info)) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            # Add file path to source data
            source_data["file_path"] = temp_file_path

            # Create source
            try:
                created = await create_source(source_data)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            source_obj: Source
            if isinstance(created, SourceProcessingResult):
                source_obj = created.source
            else:
                source_obj = created

            return {
                "source_id": source_obj.id,
                "file_name": file_info.name,
                "file_size": file_info.size,
                "mime_type": file_info.mime_type,
                "notebook_ids": notebook_ids or []
            }

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    def _get_file_extension(self, file_info: GoogleDriveFile) -> str:
        """Get appropriate file extension for Google Drive file."""
        if file_info.is_document:
            return '.pdf'
        elif file_info.is_spreadsheet:
            return '.xlsx'
        elif file_info.is_slides:
            return '.pptx'
        else:
            # Try to get extension from name
            name_parts = file_info.name.rsplit('.', 1)
            return f".{name_parts[-1]}" if len(name_parts) > 1 else ''

    async def get_user_drive_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about user's Google Drive.

        Args:
            user_id: User ID

        Returns:
            Drive information
        """
        # Check cache first
        cache_key = self._cache_key(user_id, 'drive_info')
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # Get user info
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            user_info = await self._make_api_request(user_id, user_info_url)
            if not isinstance(user_info, dict):
                raise HTTPException(status_code=500, detail="Unexpected user info response from Google Drive")

            # Get drive info
            drive_info_url = "https://www.googleapis.com/drive/v3/about"
            drive_params = {'fields': 'storageQuota,user'}
            drive_info = await self._make_api_request(user_id, f"{drive_info_url}?{urlencode(drive_params)}")
            if not isinstance(drive_info, dict):
                raise HTTPException(status_code=500, detail="Unexpected drive info response from Google Drive")

            result = {
                'user': user_info,
                'drive': drive_info,
                'connected_at': datetime.now(timezone.utc).isoformat()
            }

            # Cache the result
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Failed to get drive info for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get drive information")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()


# Global Google Drive service instance
google_drive_service = GoogleDriveService()
