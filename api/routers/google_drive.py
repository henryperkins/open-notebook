from fastapi import APIRouter, Depends, HTTPException

from api.routers.oauth import get_current_user
from api.services.google_drive_service import SearchQuery, google_drive_service

router = APIRouter()

@router.get("/google-drive/files")
async def list_google_drive_files(current_user: dict = Depends(get_current_user)):
    """
    Lists files from the user's Google Drive for the current user.
    """
    try:
        user_id = current_user.get("id", "anonymous")
        # Default: list recent files with standard page size
        result = await google_drive_service.list_files(
            user_id=user_id,
            query=SearchQuery(),
            page_token=None,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
