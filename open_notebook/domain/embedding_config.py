from typing import Optional, Sequence

from loguru import logger

from open_notebook.domain.content_settings import ContentSettings
from open_notebook.exceptions import InvalidInputError


async def get_configured_embedding_dimension() -> Optional[int]:
    """Return the configured embedding dimension from workspace settings."""
    settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]
    return settings.embedding_dimension


def ensure_embedding_dimension(
    vector: Sequence[float],
    expected_dimension: Optional[int],
    context: str,
) -> None:
    """Validate that an embedding vector matches the configured dimension."""
    if not vector or expected_dimension is None:
        return

    actual_dimension = len(vector)
    if actual_dimension != expected_dimension:
        message = (
            f"{context} produced embeddings with {actual_dimension} dimensions, "
            f"but the workspace is configured for {expected_dimension} dimensions. "
            "Update Settings → Embedding Dimension to match your embedding model, "
            "or switch to a model that returns the configured dimension."
        )
        logger.error(message)
        raise InvalidInputError(message)
