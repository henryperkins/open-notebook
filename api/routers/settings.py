from typing import Literal, Optional, cast

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import SettingsResponse, SettingsUpdate
from open_notebook.database.repository import repo_query
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.exceptions import InvalidInputError

router = APIRouter()

_EMBEDDING_INDEXES = (
    ("idx_source_embedding_embedding", "source_embedding"),
    ("idx_source_insight_embedding", "source_insight"),
    ("idx_note_embedding", "note"),
)


async def _redefine_embedding_indexes(dimension: int) -> None:
    statements = []
    for index_name, table in _EMBEDDING_INDEXES:
        statements.append(f"REMOVE INDEX IF EXISTS {index_name} ON TABLE {table};")
        statements.append(
            f"""
DEFINE INDEX {index_name} ON TABLE {table}
    FIELDS embedding
    HNSW
    DIMENSION {dimension}
    DIST COSINE;
""".strip()
        )

    await repo_query("\n".join(statements))


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get all application settings."""
    try:
        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]
        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            embedding_dimension=settings.embedding_dimension,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            google_drive_api_key=settings.google_drive_api_key,
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching settings: {str(e)}")


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(settings_update: SettingsUpdate):
    """Update application settings."""
    try:
        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]

        old_dimension: Optional[int] = settings.embedding_dimension
        target_dimension: Optional[int] = settings.embedding_dimension
        if settings_update.embedding_dimension is not None:
            target_dimension = settings_update.embedding_dimension
        dimension_changed = target_dimension != old_dimension

        if settings_update.default_content_processing_engine_doc is not None:
            settings.default_content_processing_engine_doc = cast(
                Literal["auto", "docling", "simple"],
                settings_update.default_content_processing_engine_doc,
            )
        if settings_update.default_content_processing_engine_url is not None:
            settings.default_content_processing_engine_url = cast(
                Literal["auto", "firecrawl", "jina", "simple"],
                settings_update.default_content_processing_engine_url,
            )
        if settings_update.default_embedding_option is not None:
            settings.default_embedding_option = cast(
                Literal["ask", "always", "never"],
                settings_update.default_embedding_option,
            )
        if settings_update.auto_delete_files is not None:
            settings.auto_delete_files = cast(
                Literal["yes", "no"],
                settings_update.auto_delete_files,
            )
        if settings_update.youtube_preferred_languages is not None:
            settings.youtube_preferred_languages = (
                settings_update.youtube_preferred_languages
            )
        if settings_update.google_drive_api_key is not None:
            settings.google_drive_api_key = settings_update.google_drive_api_key

        if dimension_changed and target_dimension is not None:
            try:
                await _redefine_embedding_indexes(target_dimension)
                logger.info(
                    f"Embedding index dimensions updated to {target_dimension}"
                )
                logger.warning(
                    "Rebuild existing embeddings to populate the new dimension."
                )
            except Exception as exc:
                logger.error(f"Failed to rebuild embedding indexes: {exc}")
                logger.exception(exc)
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Failed to rebuild vector indexes for the new embedding "
                        "dimension. No settings were saved."
                    ),
                ) from exc

        settings.embedding_dimension = target_dimension

        await settings.update()

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            embedding_dimension=settings.embedding_dimension,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            google_drive_api_key=settings.google_drive_api_key,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")
