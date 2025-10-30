"""
Batch upload API endpoints with comprehensive error handling and progress tracking.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from loguru import logger

from api.services.batch_upload_service import (
    batch_upload_service,
    BatchUploadResponse,
    BatchUploadStatusResponse,
    ProcessingPriority
)
# from api.auth import get_current_user  # Will be implemented when auth system is ready

# Temporary mock authentication for development
async def get_current_user():
    return {"id": "dev-user", "username": "dev"}

from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/batch-uploads", tags=["batch-uploads"])


class BatchUploadInitRequest(BaseModel):
    """Request model for batch upload initiation."""
    notebook_ids: Optional[List[str]] = Field(default=None, description="Notebook IDs to assign files to")
    priority: ProcessingPriority = Field(default=ProcessingPriority.NORMAL, description="Processing priority")
    config_override: Optional[Dict[str, Any]] = Field(default=None, description="Configuration overrides")


class BatchControlRequest(BaseModel):
    """Request model for batch control operations."""
    action: str = Field(..., description="Action: pause, resume, cancel")


@router.post("/init", response_model=BatchUploadResponse)
async def initiate_batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    notebook_ids: Optional[str] = Form(default=None),
    priority: ProcessingPriority = Form(default=ProcessingPriority.NORMAL),
    auto_start: bool = Form(default=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate a batch upload with comprehensive validation and processing.

    Args:
        background_tasks: FastAPI background tasks for async processing
        files: List of files to upload
        notebook_ids: Comma-separated notebook IDs to assign files to
        priority: Processing priority (low, normal, high, urgent)
        auto_start: Whether to automatically start processing
        current_user: Authenticated user information

    Returns:
        BatchUploadResponse: Batch upload initiation response with batch ID and status

    Raises:
        HTTPException: For validation errors or processing failures
    """

    try:
        # Parse notebook IDs
        parsed_notebook_ids = []
        if notebook_ids:
            parsed_notebook_ids = [nb_id.strip() for nb_id in notebook_ids.split(',') if nb_id.strip()]

        # Get user ID from authentication
        user_id = current_user.get("id", "anonymous")

        # Create batch upload context
        batch = await batch_upload_service.create_batch(
            files=files,
            user_id=user_id,
            notebook_ids=parsed_notebook_ids,
            priority=priority
        )

        # Prepare response
        response = BatchUploadResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            total_files=batch.total_files,
            total_size=batch.total_size,
            estimated_duration=_estimate_processing_duration(batch),
            message=f"Batch upload created with {batch.total_files} files. Processing started."
        )

        # Auto-start processing if requested
        if auto_start:
            background_tasks.add_task(
                batch_upload_service.start_batch_processing,
                batch.batch_id,
                background_tasks
            )
            response.message += " Processing started automatically."
        else:
            response.message = response.message.replace("Processing started.", "Ready to start processing.")

        logger.info(f"User {user_id} initiated batch upload {batch.batch_id} with {batch.total_files} files")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating batch upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate batch upload: {str(e)}"
        )


@router.get("/{batch_id}/status", response_model=BatchUploadStatusResponse)
async def get_batch_upload_status(
    batch_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed status of a batch upload including file-level progress.

    Args:
        batch_id: Unique identifier for the batch upload
        current_user: Authenticated user information

    Returns:
        BatchUploadStatusResponse: Comprehensive batch status with file details

    Raises:
        HTTPException: If batch not found or access denied
    """

    try:
        # Get batch status
        status = await batch_upload_service.get_batch_status(batch_id)

        # Verify user ownership (optional - depends on your security model)
        # if status.user_id != current_user.get("id"):
        #     raise HTTPException(status_code=403, detail="Access denied")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status for {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch status: {str(e)}"
        )


@router.post("/{batch_id}/control")
async def control_batch_upload(
    batch_id: str,
    control_request: BatchControlRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Control batch upload operations (pause, resume, cancel).

    Args:
        batch_id: Unique identifier for the batch upload
        control_request: Control action and parameters
        background_tasks: FastAPI background tasks for async operations
        current_user: Authenticated user information

    Returns:
        dict: Operation result and updated status

    Raises:
        HTTPException: If batch not found, access denied, or invalid action
    """

    try:
        action = control_request.action.lower()

        if action == "pause":
            await batch_upload_service.pause_batch(batch_id)
            message = "Batch upload paused successfully"

        elif action == "resume":
            await batch_upload_service.resume_batch(batch_id, background_tasks)
            message = "Batch upload resumed successfully"

        elif action == "cancel":
            await batch_upload_service.cancel_batch(batch_id)
            message = "Batch upload cancelled successfully"

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {action}. Supported actions: pause, resume, cancel"
            )

        # Get updated status
        status = await batch_upload_service.get_batch_upload_status(batch_id)

        logger.info(f"User {current_user.get('id')} {action}ed batch upload {batch_id}")

        return {
            "success": True,
            "message": message,
            "batch_id": batch_id,
            "current_status": status.status,
            "progress_percentage": status.progress_percentage
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling batch upload {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to control batch upload: {str(e)}"
        )


@router.get("/{batch_id}/files")
async def get_batch_files(
    batch_id: str,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about files in a batch upload.

    Args:
        batch_id: Unique identifier for the batch upload
        status_filter: Optional filter for file status (pending, uploading, completed, failed, etc.)
        current_user: Authenticated user information

    Returns:
        dict: File information with optional status filtering

    Raises:
        HTTPException: If batch not found or access denied
    """

    try:
        # Get batch status
        batch_status = await batch_upload_service.get_batch_status(batch_id)

        # Filter files by status if requested
        files = batch_status.files
        if status_filter:
            files = [f for f in files if f.status.value == status_filter.lower()]

        return {
            "batch_id": batch_id,
            "total_files": len(files),
            "filtered_by_status": status_filter,
            "files": [
                {
                    "file_id": f.file_id,
                    "original_filename": f.original_filename,
                    "file_size": f.file_size,
                    "mime_type": f.mime_type,
                    "status": f.status,
                    "error_message": f.error_message,
                    "retry_count": f.retry_count,
                    "upload_progress": f.upload_progress,
                    "processing_progress": f.processing_progress,
                    "notebook_ids": f.notebook_ids
                }
                for f in files
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch files for {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch files: {str(e)}"
        )


@router.get("/active")
async def get_active_batch_uploads(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of active batch uploads for the current user.

    Args:
        current_user: Authenticated user information

    Returns:
        dict: List of active batch uploads with basic status information
    """

    try:
        # Get all active batches (in a real implementation, this would query a database)
        active_batches = []

        for batch_id, batch in batch_upload_service.active_batches.items():
            # Filter by user (optional)
            # if batch.user_id != current_user.get("id"):
            #     continue

            # Only include non-completed batches
            if batch.status.value not in ["completed", "failed", "cancelled"]:
                active_batches.append({
                    "batch_id": batch.batch_id,
                    "status": batch.status,
                    "total_files": batch.total_files,
                    "processed_files": batch.processed_files,
                    "failed_files": batch.failed_files,
                    "progress_percentage": batch.progress_percentage,
                    "created_at": batch.created_at,
                    "started_at": batch.started_at,
                    "estimated_time_remaining": batch.estimated_time_remaining
                })

        return {
            "active_batches": active_batches,
            "total_active": len(active_batches)
        }

    except Exception as e:
        logger.error(f"Error getting active batch uploads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active batch uploads: {str(e)}"
        )


@router.delete("/{batch_id}")
async def delete_batch_upload(
    batch_id: str,
    force: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a batch upload and optionally cancel processing.

    Args:
        batch_id: Unique identifier for the batch upload
        force: Whether to force delete even if batch is still processing
        current_user: Authenticated user information

    Returns:
        dict: Deletion result

    Raises:
        HTTPException: If batch not found, access denied, or deletion not allowed
    """

    try:
        # Get batch status
        status = await batch_upload_service.get_batch_status(batch_id)

        # Check if batch can be deleted
        if not force and status.status.value in ["uploading", "validating", "processing"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete batch while processing. Use force=true to override."
            )

        # Cancel processing if active
        if status.status.value in ["uploading", "validating", "processing"]:
            await batch_upload_service.cancel_batch(batch_id)

        # Remove from active batches
        batch_upload_service.active_batches.pop(batch_id, None)

        logger.info(f"User {current_user.get('id')} deleted batch upload {batch_id}")

        return {
            "success": True,
            "message": f"Batch upload {batch_id} deleted successfully",
            "batch_id": batch_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting batch upload {batch_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete batch upload: {str(e)}"
        )


@router.get("/stats")
async def get_batch_upload_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get statistics about batch uploads for the current user.

    Args:
        current_user: Authenticated user information

    Returns:
        dict: Batch upload statistics
    """

    try:
        user_id = current_user.get("id", "anonymous")

        # Calculate statistics from active batches
        active_batches = [
            batch for batch in batch_upload_service.active_batches.values()
            # if batch.user_id == user_id  # Filter by user if needed
        ]

        total_batches = len(active_batches)
        processing_batches = len([b for b in active_batches if b.status.value in ["uploading", "validating", "processing"]])
        completed_batches = len([b for b in active_batches if b.status.value == "completed"])
        failed_batches = len([b for b in active_batches if b.status.value == "failed"])

        total_files = sum(b.total_files for b in active_batches)
        total_size = sum(b.total_size for b in active_batches)

        return {
            "user_id": user_id,
            "statistics": {
                "total_batches": total_batches,
                "processing_batches": processing_batches,
                "completed_batches": completed_batches,
                "failed_batches": failed_batches,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "average_batch_size": round(total_files / max(total_batches, 1), 1)
            }
        }

    except Exception as e:
        logger.error(f"Error getting batch upload stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch upload statistics: {str(e)}"
        )


def _estimate_processing_duration(batch) -> Optional[float]:
    """
    Estimate processing duration based on batch characteristics.

    Args:
        batch: BatchUploadContext instance

    Returns:
        Estimated duration in seconds, or None if cannot estimate
    """

    if not batch.files:
        return None

    # Base estimation: 5 seconds per file + 1 second per MB
    total_files = len(batch.files)
    total_size_mb = batch.total_size / (1024 * 1024)

    # Adjust based on priority
    priority_multiplier = {
        "low": 2.0,
        "normal": 1.0,
        "high": 0.5,
        "urgent": 0.25
    }.get(batch.priority.value, 1.0)

    estimated_seconds = (total_files * 5 + total_size_mb * 1) * priority_multiplier

    # Cap at reasonable maximum (1 hour)
    return min(estimated_seconds, 3600)