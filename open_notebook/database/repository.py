import asyncio
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union

from loguru import logger
from surrealdb import AsyncSurreal, RecordID  # type: ignore

T = TypeVar("T", Dict[str, Any], List[Dict[str, Any]])
ResultT = TypeVar("ResultT")

DEFAULT_MAX_RETRIES = 4
DEFAULT_BASE_DELAY_SECONDS = 0.1
DEFAULT_MAX_DELAY_SECONDS = 1.0


def _parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < 1:
            raise ValueError
        return parsed
    except ValueError:
        logger.warning(
            f"Invalid value for {name}={value!r}; falling back to {default}."
        )
        return default


def _parse_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed < 0:
            raise ValueError
        return parsed
    except ValueError:
        logger.warning(
            f"Invalid value for {name}={value!r}; falling back to {default}."
        )
        return default


MAX_RETRY_ATTEMPTS = _parse_int_env("SURREAL_MAX_RETRIES", DEFAULT_MAX_RETRIES)
BASE_RETRY_DELAY_SECONDS = _parse_float_env(
    "SURREAL_RETRY_BASE_DELAY", DEFAULT_BASE_DELAY_SECONDS
)
MAX_RETRY_DELAY_SECONDS = max(
    BASE_RETRY_DELAY_SECONDS,
    _parse_float_env("SURREAL_RETRY_MAX_DELAY", DEFAULT_MAX_DELAY_SECONDS),
)

RETRYABLE_ERROR_KEYWORDS = (
    "read or write conflict",
    "write conflict",
    "transaction cancelled",
    "transaction conflict",
    "transaction aborted",
    "deadlock",
    "timed out while waiting for table lock",
)


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(keyword in message for keyword in RETRYABLE_ERROR_KEYWORDS)


def _retry_delay_seconds(attempt: int) -> float:
    """Exponential backoff with jitter to avoid thundering herd."""
    backoff = min(
        BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)),
        MAX_RETRY_DELAY_SECONDS,
    )
    jitter = random.uniform(0, BASE_RETRY_DELAY_SECONDS)
    return backoff + jitter


async def _execute_with_retry(
    operation_name: str, executor: Callable[[AsyncSurreal], Awaitable[ResultT]]
) -> ResultT:
    attempt = 1
    while True:
        try:
            async with db_connection() as connection:
                return await executor(connection)
        except Exception as exc:
            if attempt >= MAX_RETRY_ATTEMPTS or not _is_retryable_error(exc):
                raise
            delay = _retry_delay_seconds(attempt)
            logger.warning(
                f"{operation_name} hit a retryable SurrealDB error "
                f"(attempt {attempt}/{MAX_RETRY_ATTEMPTS}); retrying in {delay:.2f}s."
            )
            await asyncio.sleep(delay)
            attempt += 1


def get_database_url():
    """Get database URL with backward compatibility"""
    surreal_url = os.getenv("SURREAL_URL")
    if surreal_url:
        return surreal_url

    # Fallback to old format - WebSocket URL format
    address = os.getenv("SURREAL_ADDRESS", "localhost")
    port = os.getenv("SURREAL_PORT", "8000")
    return f"ws://{address}:{port}/rpc"


def get_database_password():
    """Get password with backward compatibility"""
    return os.getenv("SURREAL_PASSWORD") or os.getenv("SURREAL_PASS")


def parse_record_ids(obj: Any) -> Any:
    """Recursively parse and convert RecordIDs into strings."""
    if isinstance(obj, dict):
        return {k: parse_record_ids(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [parse_record_ids(item) for item in obj]
    elif isinstance(obj, RecordID):
        return str(obj)
    return obj


def ensure_record_id(value: Union[str, RecordID]) -> RecordID:
    """Ensure a value is a RecordID."""
    if isinstance(value, RecordID):
        return value
    return RecordID.parse(value)


@asynccontextmanager
async def db_connection():
    db = AsyncSurreal(get_database_url())
    await db.signin(
        {
            "username": os.environ.get("SURREAL_USER"),
            "password": get_database_password(),
        }
    )
    await db.use(
        os.environ.get("SURREAL_NAMESPACE"), os.environ.get("SURREAL_DATABASE")
    )
    try:
        yield db
    finally:
        await db.close()


async def repo_query(
    query_str: str, vars: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute a SurrealQL query and return the results"""

    async def _executor(connection: AsyncSurreal) -> List[Dict[str, Any]]:
        result = parse_record_ids(await connection.query(query_str, vars))
        if isinstance(result, str):
            raise RuntimeError(result)
        return result

    try:
        return await _execute_with_retry("repo_query", _executor)
    except Exception as e:
        logger.error(f"Query failed: {query_str[:200]} vars: {vars}")
        logger.exception(e)
        raise


async def repo_create(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new record in the specified table"""
    # Remove 'id' attribute if it exists in data
    data.pop("id", None)
    data["created"] = datetime.now(timezone.utc)
    data["updated"] = datetime.now(timezone.utc)
    try:
        async def _executor(connection: AsyncSurreal) -> Dict[str, Any]:
            return parse_record_ids(await connection.insert(table, data))

        return await _execute_with_retry("repo_create", _executor)
    except Exception as e:
        logger.exception(e)
        raise RuntimeError("Failed to create record") from e


async def repo_relate(
    source: str, relationship: str, target: str, data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Create a relationship between two records with optional data"""
    if data is None:
        data = {}
    query = f"RELATE {source}->{relationship}->{target} CONTENT $data;"
    # logger.debug(f"Relate query: {query}")

    return await repo_query(
        query,
        {
            "data": data,
        },
    )


async def repo_upsert(
    table: str, id: Optional[str], data: Dict[str, Any], add_timestamp: bool = False
) -> List[Dict[str, Any]]:
    """Create or update a record in the specified table"""
    data.pop("id", None)
    if add_timestamp:
        data["updated"] = datetime.now(timezone.utc)
    query = f"UPSERT {id if id else table} MERGE $data;"
    return await repo_query(query, {"data": data})


async def repo_update(
    table: str, id: str, data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Update an existing record by table and id"""
    # If id already contains the table name, use it as is
    try:
        if isinstance(id, RecordID) or (":" in id and id.startswith(f"{table}:")):
            record_id = id
        else:
            record_id = f"{table}:{id}"
        data.pop("id", None)
        if "created" in data and isinstance(data["created"], str):
            data["created"] = datetime.fromisoformat(data["created"])
        data["updated"] = datetime.now(timezone.utc)
        query = f"UPDATE {record_id} MERGE $data;"
        # logger.debug(f"Update query: {query}")
        result = await repo_query(query, {"data": data})
        # if isinstance(result, list):
        #     return [_return_data(item) for item in result]
        return parse_record_ids(result)
    except Exception as e:
        raise RuntimeError(f"Failed to update record: {str(e)}")


async def repo_get_news_by_jota_id(jota_id: str) -> Dict[str, Any]:
    try:
        results = await repo_query(
            "SELECT * omit embedding FROM news where jota_id=$jota_id",
            {"jota_id": jota_id},
        )
        return parse_record_ids(results)
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to fetch record: {str(e)}")


async def repo_delete(record_id: Union[str, RecordID]):
    """Delete a record by record id"""

    try:
        async def _executor(connection: AsyncSurreal):
            return await connection.delete(ensure_record_id(record_id))

        return await _execute_with_retry("repo_delete", _executor)
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete record: {str(e)}") from e


async def repo_insert(
    table: str, data: List[Dict[str, Any]], ignore_duplicates: bool = False
) -> List[Dict[str, Any]]:
    """Create a new record in the specified table"""
    try:
        async def _executor(connection: AsyncSurreal) -> List[Dict[str, Any]]:
            return parse_record_ids(await connection.insert(table, data))

        return await _execute_with_retry("repo_insert", _executor)
    except Exception as e:
        if ignore_duplicates and "already contains" in str(e):
            return []
        logger.exception(e)
        raise RuntimeError("Failed to create record") from e
