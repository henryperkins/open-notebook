"""
Advanced batch upload service with comprehensive error handling, progress tracking,
and intelligent processing strategies.
"""

import asyncio
import hashlib
import mimetypes
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

import aiofiles  # type: ignore[import-untyped]
import aiofiles.os  # type: ignore[import-untyped]
import psutil  # type: ignore[import-untyped]
from fastapi import BackgroundTasks, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel, Field, validator

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Notebook, Source


class BatchStatus(str, Enum):
    """Batch processing states with detailed lifecycle management."""
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class FileStatus(str, Enum):
    """Individual file processing states."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class ProcessingPriority(str, Enum):
    """Priority levels for batch processing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BatchUploadConfig:
    """Configuration for batch upload behavior."""
    max_concurrent_uploads: int = 3
    max_concurrent_processing: int = 2
    max_file_size_mb: int = 100
    max_batch_size: int = 50
    chunk_size: int = 8192
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    progress_update_interval: float = 0.5
    cleanup_temp_files: bool = True
    validate_mime_types: bool = True
    allowed_extensions: set = field(default_factory=lambda: {
        '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        '.mp3', '.wav', '.mp4', '.avi', '.mov',
        '.csv', '.xlsx', '.json', '.xml', '.html'
    })
    blocked_extensions: set = field(default_factory=lambda: {
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm'
    })


@dataclass
class FileProcessingContext:
    """Context for individual file processing with retry logic."""
    file: UploadFile
    file_id: str
    original_filename: str
    file_path: Optional[str] = None
    file_size: int = 0
    mime_type: str = ""
    checksum: str = ""
    status: FileStatus = FileStatus.PENDING
    error_message: str = ""
    retry_count: int = 0
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    upload_progress: float = 0.0
    processing_progress: float = 0.0
    notebook_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class BatchUploadContext:
    """Comprehensive context for batch upload operations."""
    batch_id: str
    user_id: str
    status: BatchStatus = BatchStatus.INITIALIZING
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: List[FileProcessingContext] = field(default_factory=list)
    config: BatchUploadConfig = field(default_factory=BatchUploadConfig)
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_size: int = 0
    uploaded_size: int = 0
    progress_percentage: float = 0.0
    estimated_time_remaining: Optional[float] = None
    error_summary: Dict[str, int] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    cancellation_requested: bool = False
    pause_requested: bool = False


# Pydantic Models for API Responses
class FileProcessingInfo(BaseModel):
    """Information about a single file in the batch."""
    file_id: str
    original_filename: str
    file_size: int
    mime_type: str
    status: FileStatus
    error_message: Optional[str] = None
    retry_count: int = 0
    upload_progress: float = 0.0
    processing_progress: float = 0.0
    notebook_ids: List[str] = []


class BatchUploadResponse(BaseModel):
    """Response for batch upload initiation."""
    batch_id: str
    status: BatchStatus
    total_files: int
    total_size: int
    estimated_duration: Optional[float] = None
    message: str


class BatchUploadStatusResponse(BaseModel):
    """Detailed status response for batch uploads."""
    batch_id: str
    status: BatchStatus
    progress_percentage: float
    total_files: int
    processed_files: int
    failed_files: int
    skipped_files: int
    total_size: int
    uploaded_size: int
    files: List[FileProcessingInfo]
    estimated_time_remaining: Optional[float] = None
    error_summary: Dict[str, int] = {}
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AdvancedBatchUploadService:
    """Sophisticated batch upload service with intelligent processing capabilities."""

    def __init__(self):
        self.active_batches: Dict[str, BatchUploadContext] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.config = BatchUploadConfig()
        self._system_monitor = SystemMonitor()

    async def create_batch(
        self,
        files: List[UploadFile],
        user_id: str,
        notebook_ids: Optional[List[str]] = None,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        config_override: Optional[Dict] = None
    ) -> BatchUploadContext:
        """Create a new batch upload context with comprehensive validation."""

        # Validate input parameters
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        if len(files) > self.config.max_batch_size:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {self.config.max_batch_size} files allowed per batch"
            )

        # Override config if provided
        if config_override:
            config = BatchUploadConfig(**{**self.config.__dict__, **config_override})
        else:
            config = self.config

        # Create batch context
        batch_id = str(uuid.uuid4())
        batch = BatchUploadContext(
            batch_id=batch_id,
            user_id=user_id,
            priority=priority,
            config=config,
            metadata={
                "client_ip": "unknown",  # Would be set from request
                "user_agent": "unknown",  # Would be set from request
                "upload_source": "web_interface"
            }
        )

        # Process and validate each file
        total_size = 0
        for file in files:
            file_context = await self._create_file_context(file, notebook_ids or [])
            batch.files.append(file_context)
            total_size += file_context.file_size

        batch.total_files = len(files)
        batch.total_size = total_size

        # Store batch context
        self.active_batches[batch_id] = batch

        logger.info(f"Created batch {batch_id} with {len(files)} files, total size: {total_size} bytes")

        return batch

    async def _create_file_context(
        self,
        file: UploadFile,
        notebook_ids: List[str]
    ) -> FileProcessingContext:
        """Create file processing context with validation."""

        file_id = str(uuid.uuid4())
        original_filename = file.filename or "unknown"

        # Read file to determine size and calculate checksum
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset file pointer

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Validate file
        await self._validate_file(original_filename, file_size, mime_type, content)

        return FileProcessingContext(
            file=file,
            file_id=file_id,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
            notebook_ids=notebook_ids,
            metadata={
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "original_extension": Path(original_filename).suffix.lower()
            }
        )

    async def _validate_file(
        self,
        filename: str,
        size: int,
        mime_type: str,
        content: bytes
    ) -> None:
        """Comprehensive file validation with security checks."""

        # Size validation
        if size == 0:
            raise HTTPException(status_code=400, detail=f"File {filename} is empty")

        if size > self.config.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {filename} exceeds maximum size of {self.config.max_file_size_mb}MB"
            )

        # Extension validation
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.config.blocked_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} is not allowed for security reasons"
            )

        if self.config.allowed_extensions and file_ext not in self.config.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} is not supported. Supported types: {', '.join(self.config.allowed_extensions)}"
            )

        # MIME type validation
        if self.config.validate_mime_types:
            allowed_mimes = self._get_allowed_mime_types()
            if mime_type not in allowed_mimes:
                raise HTTPException(
                    status_code=400,
                    detail=f"MIME type {mime_type} is not supported"
                )

        # Content validation (basic security check)
        await self._validate_content(content, filename)

    def _get_allowed_mime_types(self) -> set:
        """Get set of allowed MIME types based on file extensions."""
        mime_types = set()
        for ext in self.config.allowed_extensions:
            mime_type, _ = mimetypes.guess_type(f"file{ext}")
            if mime_type:
                mime_types.add(mime_type)
        return mime_types

    async def _validate_content(self, content: bytes, filename: str) -> None:
        """Validate file content for security threats."""

        # Check for common malicious patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'data:text/html',
            b'<?php',
            b'<%',
            b'eval(',
            b'exec(',
        ]

        content_lower = content[:1024].lower()  # Check first 1KB

        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(f"Suspicious content detected in file: {filename}")
                raise HTTPException(
                    status_code=400,
                    detail=f"File {filename} contains potentially malicious content"
                )

    async def start_batch_processing(
        self,
        batch_id: str,
        background_tasks: BackgroundTasks
    ) -> None:
        """Start asynchronous batch processing with intelligent queue management."""

        if batch_id not in self.active_batches:
            raise HTTPException(status_code=404, detail="Batch not found")

        batch = self.active_batches[batch_id]
        batch.status = BatchStatus.UPLOADING
        batch.started_at = datetime.now(timezone.utc)

        # Queue background processing
        background_tasks.add_task(self._process_batch_async, batch_id)

        logger.info(f"Started processing batch {batch_id}")

    async def _process_batch_async(self, batch_id: str) -> None:
        """Asynchronous batch processing with concurrent control and error handling."""

        batch = self.active_batches.get(batch_id)
        if not batch:
            logger.error(f"Batch {batch_id} not found during processing")
            return

        try:
            # Monitor system resources
            if not await self._system_monitor.can_process_batch():
                logger.warning(f"System resources too low, pausing batch {batch_id}")
                batch.status = BatchStatus.PAUSED
                await asyncio.sleep(5)  # Wait before retrying
                batch.status = BatchStatus.UPLOADING

            # Phase 1: Upload all files
            await self._upload_files_concurrently(batch)

            # Phase 2: Validate uploaded files
            await self._validate_uploaded_files(batch)

            # Phase 3: Process files into sources
            await self._process_files_to_sources(batch)

            # Complete batch
            batch.status = BatchStatus.COMPLETED
            batch.completed_at = datetime.now(timezone.utc)
            batch.progress_percentage = 100.0

            logger.info(f"Completed batch {batch_id}: {batch.processed_files} processed, {batch.failed_files} failed")

        except Exception as e:
            logger.error(f"Batch {batch_id} failed: {str(e)}")
            batch.status = BatchStatus.FAILED
            batch.error_summary["general_error"] = 1
            batch.completed_at = datetime.now(timezone.utc)

        finally:
            # Cleanup
            await self._cleanup_batch(batch)

    async def _upload_files_concurrently(self, batch: BatchUploadContext) -> None:
        """Upload files concurrently with progress tracking and error handling."""

        semaphore = asyncio.Semaphore(batch.config.max_concurrent_uploads)
        upload_tasks = []

        for file_context in batch.files:
            if batch.cancellation_requested:
                break

            task = asyncio.create_task(
                self._upload_single_file_with_semaphore(semaphore, file_context, batch)
            )
            upload_tasks.append(task)

        # Wait for all uploads to complete
        await asyncio.gather(*upload_tasks, return_exceptions=True)

    async def _upload_single_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file_context: FileProcessingContext,
        batch: BatchUploadContext
    ) -> None:
        """Upload single file with semaphore control and retry logic."""

        async with semaphore:
            await self._upload_single_file(file_context, batch)

    async def _upload_single_file(
        self,
        file_context: FileProcessingContext,
        batch: BatchUploadContext
    ) -> None:
        """Upload single file with comprehensive error handling and retry logic."""

        file_context.status = FileStatus.UPLOADING
        file_context.processing_start_time = datetime.now(timezone.utc)

        for attempt in range(batch.config.retry_attempts + 1):
            try:
                if batch.cancellation_requested:
                    file_context.status = FileStatus.FAILED
                    file_context.error_message = "Upload cancelled"
                    return

                # Generate unique filename
                unique_filename = self._generate_unique_filename(
                    file_context.original_filename,
                    batch.batch_id
                )
                file_path = Path(UPLOADS_FOLDER) / batch.batch_id / unique_filename

                # Create directory if it doesn't exist
                await aiofiles.os.makedirs(file_path.parent, exist_ok=True)

                # Upload file with progress tracking
                uploaded_size = 0
                total_size = file_context.file_size

                async with aiofiles.open(file_path, 'wb') as f:
                    while chunk := await file_context.file.read(batch.config.chunk_size):
                        if batch.cancellation_requested:
                            await f.close()
                            await aiofiles.os.remove(file_path)
                            file_context.status = FileStatus.FAILED
                            file_context.error_message = "Upload cancelled"
                            return

                        await f.write(chunk)
                        uploaded_size += len(chunk)
                        file_context.upload_progress = (uploaded_size / total_size) * 100
                        batch.uploaded_size += len(chunk)
                        batch.progress_percentage = (batch.uploaded_size / batch.total_size) * 50  # Upload is 50% of total progress

                        # Update progress periodically
                        if attempt == 0:  # Only update on first attempt to avoid spamming
                            await self._update_batch_progress(batch)

                file_context.file_path = str(file_path)
                file_context.status = FileStatus.UPLOADED
                file_context.upload_progress = 100.0

                logger.info(f"Successfully uploaded {file_context.original_filename} to {file_path}")
                return

            except Exception as e:
                file_context.retry_count = attempt + 1
                error_msg = f"Upload attempt {attempt + 1} failed: {str(e)}"
                file_context.error_message = error_msg

                logger.warning(f"{error_msg} for {file_context.original_filename}")

                if attempt < batch.config.retry_attempts:
                    file_context.status = FileStatus.RETRYING
                    await asyncio.sleep(batch.config.retry_delay_seconds * (2 ** attempt))  # Exponential backoff
                    await file_context.file.seek(0)  # Reset file pointer
                else:
                    file_context.status = FileStatus.FAILED
                    batch.failed_files += 1
                    batch.error_summary[f"upload_error_{type(e).__name__}"] = batch.error_summary.get(f"upload_error_{type(e).__name__}", 0) + 1

    def _generate_unique_filename(self, original_filename: str, batch_id: str) -> str:
        """Generate unique filename with batch prefix and timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix
        name_without_ext = Path(original_filename).stem

        # Sanitize filename
        safe_name = "".join(c for c in name_without_ext if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')[:50]  # Limit length

        return f"{batch_id}_{timestamp}_{safe_name}{file_ext}"

    async def _validate_uploaded_files(self, batch: BatchUploadContext) -> None:
        """Validate uploaded files for integrity and security."""

        batch.status = BatchStatus.VALIDATING

        for file_context in batch.files:
            if batch.cancellation_requested:
                break

            if file_context.status != FileStatus.UPLOADED:
                continue

            file_context.status = FileStatus.VALIDATING

            try:
                # Verify file exists and has correct size
                if not file_context.file_path:
                    raise ValueError("File path not set")

                file_path = Path(file_context.file_path)
                if not await aiofiles.os.path.exists(file_path):
                    raise ValueError("Uploaded file not found")

                actual_size = (await aiofiles.os.stat(file_path)).st_size
                if actual_size != file_context.file_size:
                    raise ValueError(f"File size mismatch: expected {file_context.file_size}, got {actual_size}")

                # Verify checksum
                async with aiofiles.open(file_path, 'rb') as f:
                    content = await f.read()
                    actual_checksum = hashlib.sha256(content).hexdigest()
                    if actual_checksum != file_context.checksum:
                        raise ValueError("File checksum mismatch")

                file_context.status = FileStatus.VALIDATED

            except Exception as e:
                file_context.status = FileStatus.FAILED
                file_context.error_message = f"Validation failed: {str(e)}"
                batch.failed_files += 1
                batch.error_summary[f"validation_error_{type(e).__name__}"] = batch.error_summary.get(f"validation_error_{type(e).__name__}", 0) + 1
                logger.error(f"Validation failed for {file_context.original_filename}: {str(e)}")

    async def _process_files_to_sources(self, batch: BatchUploadContext) -> None:
        """Process validated files into sources with concurrent control."""

        batch.status = BatchStatus.PROCESSING

        # Get validated files
        validated_files = [f for f in batch.files if f.status == FileStatus.VALIDATED]

        # Process concurrently with limited workers
        semaphore = asyncio.Semaphore(batch.config.max_concurrent_processing)
        processing_tasks = []

        for file_context in validated_files:
            if batch.cancellation_requested:
                break

            task = asyncio.create_task(
                self._process_file_to_source_with_semaphore(semaphore, file_context, batch)
            )
            processing_tasks.append(task)

        # Wait for all processing to complete
        await asyncio.gather(*processing_tasks, return_exceptions=True)

    async def _process_file_to_source_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file_context: FileProcessingContext,
        batch: BatchUploadContext
    ) -> None:
        """Process single file to source with semaphore control."""

        async with semaphore:
            await self._process_file_to_source(file_context, batch)

    async def _process_file_to_source(
        self,
        file_context: FileProcessingContext,
        batch: BatchUploadContext
    ) -> None:
        """Process single file into source with comprehensive error handling."""

        file_context.status = FileStatus.PROCESSING

        try:
            if batch.cancellation_requested:
                file_context.status = FileStatus.FAILED
                file_context.error_message = "Processing cancelled"
                return

            # Create source using existing source creation logic
            from api.sources_service import SourceProcessingResult, create_source

            source_data = {
                "title": file_context.original_filename,
                "type": "upload",
                "file_path": file_context.file_path,
                "notebooks": file_context.notebook_ids,
                "delete_source": True,  # Delete after processing
                "async_processing": True,
                "batch_id": batch.batch_id,
                "file_metadata": {
                    "original_filename": file_context.original_filename,
                    "file_size": file_context.file_size,
                    "mime_type": file_context.mime_type,
                    "checksum": file_context.checksum,
                    "upload_timestamp": file_context.metadata.get("upload_timestamp")
                }
            }

            # Create source
            source_result = await create_source(source_data)
            if isinstance(source_result, SourceProcessingResult):
                source_obj = source_result.source
            else:
                source_obj = source_result

            file_context.status = FileStatus.COMPLETED
            file_context.processing_progress = 100.0
            batch.processed_files += 1

            # Update progress (processing is 50% of total progress)
            batch.progress_percentage = 50.0 + (batch.processed_files / len(batch.files)) * 50.0

            logger.info(f"Successfully processed {file_context.original_filename} to source {source_obj.id}")

        except Exception as e:
            file_context.status = FileStatus.FAILED
            file_context.error_message = f"Processing failed: {str(e)}"
            batch.failed_files += 1
            batch.error_summary[f"processing_error_{type(e).__name__}"] = batch.error_summary.get(f"processing_error_{type(e).__name__}", 0) + 1
            logger.error(f"Processing failed for {file_context.original_filename}: {str(e)}")

    async def _update_batch_progress(self, batch: BatchUploadContext) -> None:
        """Update batch progress and calculate estimated time remaining."""

        current_time = datetime.now(timezone.utc)

        if batch.started_at and batch.progress_percentage > 0:
            elapsed_time = (current_time - batch.started_at).total_seconds()
            if batch.progress_percentage < 100:
                batch.estimated_time_remaining = (elapsed_time / batch.progress_percentage) * (100 - batch.progress_percentage)

        # Progress would be stored in database or cache for real-time updates
        pass

    async def _cleanup_batch(self, batch: BatchUploadContext) -> None:
        """Cleanup temporary files and batch context."""

        if batch.config.cleanup_temp_files:
            # Cleanup temporary files after a delay
            await asyncio.sleep(300)  # Wait 5 minutes before cleanup

            try:
                batch_dir = Path(UPLOADS_FOLDER) / batch.batch_id
                if await aiofiles.os.path.exists(batch_dir):
                    import shutil
                    shutil.rmtree(batch_dir)
                    logger.info(f"Cleaned up batch directory: {batch_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup batch directory {batch.batch_id}: {str(e)}")

        # Remove from active batches after some time
        await asyncio.sleep(3600)  # Keep in memory for 1 hour
        self.active_batches.pop(batch.batch_id, None)

    async def get_batch_status(self, batch_id: str) -> BatchUploadStatusResponse:
        """Get comprehensive batch status with file details."""

        batch = self.active_batches.get(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        files_info = [
            FileProcessingInfo(
                file_id=f.file_id,
                original_filename=f.original_filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                status=f.status,
                error_message=f.error_message if f.status == FileStatus.FAILED else None,
                retry_count=f.retry_count,
                upload_progress=f.upload_progress,
                processing_progress=f.processing_progress,
                notebook_ids=f.notebook_ids
            )
            for f in batch.files
        ]

        return BatchUploadStatusResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            progress_percentage=batch.progress_percentage,
            total_files=batch.total_files,
            processed_files=batch.processed_files,
            failed_files=batch.failed_files,
            skipped_files=batch.skipped_files,
            total_size=batch.total_size,
            uploaded_size=batch.uploaded_size,
            files=files_info,
            estimated_time_remaining=batch.estimated_time_remaining,
            error_summary=batch.error_summary,
            created_at=batch.created_at,
            started_at=batch.started_at,
            completed_at=batch.completed_at
        )

    async def cancel_batch(self, batch_id: str) -> None:
        """Cancel batch processing."""

        batch = self.active_batches.get(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        if batch.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed batch")

        batch.cancellation_requested = True
        batch.status = BatchStatus.CANCELLED
        batch.completed_at = datetime.now(timezone.utc)

        logger.info(f"Cancelled batch {batch_id}")

    async def pause_batch(self, batch_id: str) -> None:
        """Pause batch processing."""

        batch = self.active_batches.get(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        if batch.status not in [BatchStatus.UPLOADING, BatchStatus.VALIDATING, BatchStatus.PROCESSING]:
            raise HTTPException(status_code=400, detail="Cannot pause batch in current state")

        batch.pause_requested = True
        batch.status = BatchStatus.PAUSED

        logger.info(f"Paused batch {batch_id}")

    async def resume_batch(self, batch_id: str, background_tasks: BackgroundTasks) -> None:
        """Resume paused batch processing."""

        batch = self.active_batches.get(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        if batch.status != BatchStatus.PAUSED:
            raise HTTPException(status_code=400, detail="Batch is not paused")

        batch.pause_requested = False
        batch.status = BatchStatus.UPLOADING

        # Resume processing
        background_tasks.add_task(self._process_batch_async, batch_id)

        logger.info(f"Resumed batch {batch_id}")


class SystemMonitor:
    """Monitor system resources for intelligent batch processing."""

    def __init__(self):
        self.max_cpu_usage = 80.0  # Maximum CPU usage percentage
        self.max_memory_usage = 85.0  # Maximum memory usage percentage

    async def can_process_batch(self) -> bool:
        """Check if system has enough resources for batch processing."""

        try:
            # Check CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage > self.max_cpu_usage:
                logger.warning(f"High CPU usage: {cpu_usage}%")
                return False

            # Check memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            if memory_usage > self.max_memory_usage:
                logger.warning(f"High memory usage: {memory_usage}%")
                return False

            # Check disk space
            disk = psutil.disk_usage(UPLOADS_FOLDER)
            if disk.free < 1024 * 1024 * 1024:  # Less than 1GB free
                logger.warning(f"Low disk space: {disk.free / (1024**3):.1f}GB free")
                return False

            return True

        except Exception as e:
            logger.error(f"Error monitoring system resources: {str(e)}")
            return True  # Default to allowing processing if monitoring fails


# Global service instance
batch_upload_service = AdvancedBatchUploadService()
