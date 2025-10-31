# Open Notebook - Development Guidelines

## Code Quality Standards

### Python Code Formatting
- **Line Length**: 88 characters (Black/Ruff standard)
- **Import Organization**: Grouped and sorted (stdlib → third-party → local)
- **Type Hints**: Used extensively with Python 3.11+ syntax
- **Docstrings**: Triple-quoted strings for modules, classes, and complex functions
- **String Quotes**: Double quotes for strings, single quotes for dict keys when needed

### TypeScript/React Code Formatting
- **Quotes**: Single quotes for strings, double quotes for JSX attributes
- **Semicolons**: Not used (Next.js/modern React convention)
- **Component Style**: Functional components with hooks
- **File Extensions**: `.tsx` for components, `.ts` for utilities
- **Naming**: PascalCase for components, camelCase for functions/variables

### Structural Conventions

#### Python Project Structure
- **API Layer**: FastAPI routers in `/api/routers`, services in `/api/services`
- **Domain Layer**: Business entities in `/open_notebook/domain`
- **Database Layer**: Repository pattern in `/open_notebook/database`
- **Background Jobs**: Command pattern in `/commands` directory
- **Tests**: Mirror source structure in `/tests` directory

#### Frontend Structure
- **Components**: Organized by feature in `/src/components`
- **API Clients**: Centralized in `/src/lib/api`
- **Hooks**: Custom hooks in `/src/lib/hooks`
- **Types**: TypeScript types in `/src/lib/types`
- **State**: Zustand stores for global state, React Query for server state

### Naming Conventions

#### Python
- **Classes**: PascalCase (e.g., `SourceProcessingInput`, `BatchUploadService`)
- **Functions/Methods**: snake_case (e.g., `create_source`, `get_latest_version`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `UPLOADS_FOLDER`, `MAX_FILE_SIZE`)
- **Private Methods**: Leading underscore (e.g., `_validate_file`, `_cleanup_batch`)
- **Async Functions**: Prefix with `async def`, no special naming

#### TypeScript/React
- **Components**: PascalCase (e.g., `GeneratePodcastDialog`, `SourceListResponse`)
- **Functions**: camelCase (e.g., `handleSubmit`, `buildContentFromSelections`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SOURCE_MODES`, `QUERY_KEYS`)
- **Interfaces/Types**: PascalCase with descriptive names (e.g., `NotebookSelection`)
- **Props Interfaces**: Component name + `Props` suffix

## Semantic Patterns

### Error Handling

#### Python Pattern
```python
try:
    # Operation
    result = await some_operation()
except HTTPException:
    # Re-raise HTTP exceptions without modification
    raise
except SpecificError as e:
    # Handle specific errors with context
    logger.error(f"Operation failed: {str(e)}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    # Catch-all with logging
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
finally:
    # Cleanup resources
    await cleanup()
```

**Frequency**: Used in 100% of API endpoints and service methods

#### TypeScript Pattern
```typescript
try {
  const result = await apiCall()
  // Success handling
} catch (error) {
  console.error('Operation failed:', error)
  toast({
    title: 'Operation failed',
    description: error instanceof Error ? error.message : 'Please try again',
    variant: 'destructive',
  })
}
```

**Frequency**: Used in all async operations with user feedback

### Async/Await Patterns

#### Python Async Operations
```python
async def process_items(items: List[Item]) -> None:
    """Process items concurrently with semaphore control."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def process_with_limit(item: Item):
        async with semaphore:
            return await process_single_item(item)
    
    tasks = [process_with_limit(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Frequency**: Used in batch operations, file uploads, and concurrent processing (5+ occurrences)

#### React Async with Loading States
```typescript
const [isLoading, setIsLoading] = useState(false)

const handleOperation = useCallback(async () => {
  setIsLoading(true)
  try {
    await performOperation()
  } finally {
    setIsLoading(false)
  }
}, [dependencies])
```

**Frequency**: Standard pattern for all user-initiated async operations

### Database Operations

#### Repository Pattern
```python
# Query with parameters
result = await repo_query(
    "SELECT * FROM source WHERE notebook = $notebook_id",
    {"notebook_id": ensure_record_id(notebook_id)}
)

# Save domain entity
source = Source(title="Example", topics=[])
await source.save()

# Get by ID
source = await Source.get(source_id)
```

**Frequency**: Used in 100% of database interactions

#### Record ID Handling
```python
# Always ensure proper record ID format
record_id = ensure_record_id(source_id)  # Adds table prefix if missing
```

**Frequency**: Used before all database queries with IDs (20+ occurrences)

### API Response Patterns

#### FastAPI Endpoint Structure
```python
@router.post("/endpoint", response_model=ResponseModel)
async def endpoint_handler(
    request: RequestModel,
    dependency: Type = Depends(get_dependency)
):
    """Endpoint description."""
    try:
        # Validate input
        if not request.field:
            raise HTTPException(status_code=400, detail="Field required")
        
        # Business logic
        result = await service.process(request)
        
        # Return response
        return ResponseModel(
            id=result.id,
            field=result.field,
            created=str(result.created)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
```

**Frequency**: Standard pattern for all API endpoints (50+ endpoints)

### React Component Patterns

#### Custom Hooks for Data Fetching
```typescript
// Using TanStack Query
const { data, isLoading, error } = useQuery({
  queryKey: QUERY_KEYS.sources(notebookId),
  queryFn: () => sourcesApi.list({ notebook_id: notebookId }),
  enabled: Boolean(notebookId),
})
```

**Frequency**: Used for all server data fetching (30+ occurrences)

#### State Management with Callbacks
```typescript
const handleChange = useCallback((value: string) => {
  setState(value)
  // Additional logic
}, [dependencies])

useEffect(() => {
  // Effect logic
}, [dependencies])
```

**Frequency**: Standard pattern for event handlers and effects

### Logging Patterns

#### Python Logging with Loguru
```python
from loguru import logger

# Info logging
logger.info(f"Processing source {source_id}")

# Warning with context
logger.warning(f"Failed to get status for source {source_id}: {error}")

# Error with full context
logger.error(f"Batch {batch_id} failed: {str(e)}")
```

**Frequency**: Used throughout codebase (100+ occurrences)

### Background Job Patterns

#### Command Definition
```python
from pydantic import BaseModel
from surreal_commands import command

class CommandInput(BaseModel):
    source_id: str
    content_state: dict
    embed: bool = True

@command(app_name="open_notebook")
async def process_source(input: CommandInput):
    """Process source in background."""
    # Import inside to avoid circular dependencies
    from open_notebook.graphs.source import graph
    
    # Execute workflow
    result = await graph.ainvoke(input.model_dump())
    return result
```

**Frequency**: Pattern used for all background jobs (10+ commands)

#### Command Submission
```python
command_id = await CommandService.submit_command_job(
    "open_notebook",  # app name
    "process_source",  # command name
    command_input.model_dump(),
)
```

**Frequency**: Used whenever async processing is needed (15+ occurrences)

### Form Handling Patterns

#### FastAPI Form Data Parsing
```python
def parse_form_data(
    field: str = Form(...),
    optional_field: Optional[str] = Form(None),
    json_field: Optional[str] = Form(None),
) -> tuple[Model, Optional[UploadFile]]:
    """Parse multipart form data into model."""
    # Parse JSON strings
    parsed_json = json.loads(json_field) if json_field else []
    
    # Create model
    model = Model(field=field, parsed=parsed_json)
    return model, file
```

**Frequency**: Used for all file upload endpoints (5+ occurrences)

#### React Form with React Hook Form
```typescript
const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: { field: '' },
})

const onSubmit = form.handleSubmit(async (values) => {
  await mutation.mutateAsync(values)
})
```

**Frequency**: Standard pattern for all forms (20+ forms)

### Testing Patterns

#### Pytest with Mocking
```python
@pytest.mark.asyncio
@patch("module.dependency")
async def test_function(mock_dependency, client):
    """Test description."""
    # Setup mock
    mock_dependency.return_value = expected_value
    
    # Execute
    response = client.post("/endpoint", json=payload)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["field"] == expected_value
```

**Frequency**: Standard pattern for all API tests (30+ tests)

## Internal API Usage

### SurrealDB Repository Pattern
```python
from open_notebook.database.repository import repo_query, ensure_record_id

# Query with parameters
results = await repo_query(
    "SELECT * FROM table WHERE field = $param",
    {"param": value}
)

# Ensure record ID format
record_id = ensure_record_id("source:123")  # Returns "source:123"
record_id = ensure_record_id("123")  # Returns "source:123" if context is source
```

### Domain Model Operations
```python
from open_notebook.domain.notebook import Source, Notebook

# Create and save
source = Source(title="Example", topics=[], asset=Asset(file_path=path))
await source.save()

# Get by ID
source = await Source.get(source_id)

# Update
source.title = "Updated"
await source.save()

# Delete
await source.delete()

# Relationships
await source.add_to_notebook(notebook_id)
```

### AI Graph Invocation
```python
from open_notebook.graphs.source import graph as source_graph

# Invoke graph with input
result = await source_graph.ainvoke({
    "source": source,
    "transformation": transformation,
})
```

### Command Service Usage
```python
from api.command_service import CommandService

# Submit async job
command_id = await CommandService.submit_command_job(
    app_name="open_notebook",
    command_name="process_source",
    input_data=input_dict,
)

# Get status
from surreal_commands import get_command_status
status = await get_command_status(command_id)
```

### Command Definition with Decorator
```python
from surreal_commands import command, CommandInput, CommandOutput
from pydantic import BaseModel

class ProcessInput(CommandInput):
    source_id: str
    options: dict

class ProcessOutput(CommandOutput):
    success: bool
    processing_time: float
    error_message: Optional[str] = None

@command("process_source", app="open_notebook")
async def process_source_command(input_data: ProcessInput) -> ProcessOutput:
    """Command handler with typed input/output."""
    try:
        # Process logic
        result = await process(input_data)
        return ProcessOutput(success=True, processing_time=elapsed)
    except Exception as e:
        return ProcessOutput(success=False, error_message=str(e))
```

### React Query Keys
```typescript
import { QUERY_KEYS } from '@/lib/api/query-client'

// Centralized query key factory
export const QUERY_KEYS = {
  notebooks: ['notebooks'] as const,
  notebook: (id: string) => ['notebooks', id] as const,
  sources: (notebookId?: string) => ['sources', notebookId] as const,
  source: (id: string) => ['sources', id] as const,
}

// Usage in hooks
const { data } = useQuery({
  queryKey: QUERY_KEYS.sources(notebookId),
  queryFn: () => api.list({ notebook_id: notebookId }),
})

// Invalidate after mutation
queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources(notebookId) })
```

### Query Client Configuration
```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes
      gcTime: 10 * 60 * 1000,         // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})
```

### FastAPI Application Patterns

#### Lifespan Events
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup: Run migrations
    logger.info("Starting API initialization...")
    migration_manager = AsyncMigrationManager()
    await migration_manager.run_migration_up()
    
    yield  # Application runs
    
    # Shutdown: cleanup
    logger.info("API shutdown complete")

app = FastAPI(lifespan=lifespan)
```

**Frequency**: Used in main.py for application lifecycle (1 occurrence)

#### Middleware Stack
```python
# Order matters: last added = first executed
app.add_middleware(SessionMiddleware, secret_key=secret)
app.add_middleware(PasswordAuthMiddleware, excluded_paths=[...])
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

**Frequency**: Standard middleware configuration (1 occurrence)

#### Router Organization
```python
from api.routers import notebooks, sources, chat

app.include_router(notebooks.router, prefix="/api", tags=["notebooks"])
app.include_router(sources.router, prefix="/api", tags=["sources"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
```

**Frequency**: All routers follow this pattern (20+ routers)

## Common Code Idioms

### Python Context Managers
```python
# Database connection
async with db_connection() as connection:
    result = await connection.query(sql)

# File operations
async with aiofiles.open(path, 'wb') as f:
    await f.write(content)

# Semaphore control
async with semaphore:
    await process_item()
```

### TypeScript Optional Chaining
```typescript
// Safe property access
const value = object?.property?.nested ?? defaultValue

// Safe array access
const items = data?.items ?? []

// Safe function call
callback?.()
```

### Python List Comprehensions
```python
# Filter and transform
valid_items = [item.id for item in items if item.is_valid]

# Dictionary comprehension
config = {k: v for k, v in data.items() if v is not None}
```

### React useMemo/useCallback
```typescript
// Memoize expensive computations
const computed = useMemo(() => {
  return expensiveOperation(data)
}, [data])

// Memoize callbacks
const handler = useCallback(() => {
  performAction()
}, [dependencies])
```

## Annotations and Decorators

### Python Type Annotations
```python
from typing import List, Optional, Dict, Any, Literal

async def function(
    param: str,
    optional: Optional[int] = None,
    items: List[Dict[str, Any]] = []
) -> Optional[Result]:
    """Function with full type hints."""
    pass
```

### FastAPI Dependency Injection
```python
from fastapi import Depends, Query, Form, File

@router.get("/endpoint")
async def handler(
    param: str = Query(..., description="Required parameter"),
    optional: Optional[str] = Query(None),
    dependency: Type = Depends(get_dependency)
):
    pass
```

### Pydantic Model Validators
```python
from pydantic import BaseModel, Field, validator

class Model(BaseModel):
    field: str = Field(..., description="Field description")
    
    @validator('field')
    def validate_field(cls, v):
        if not v:
            raise ValueError("Field required")
        return v
```

### React Component Props
```typescript
interface ComponentProps {
  required: string
  optional?: number
  callback: (value: string) => void
  children?: React.ReactNode
}

export function Component({ required, optional, callback }: ComponentProps) {
  // Component implementation
}
```

### LangGraph Workflow Patterns

#### Graph Definition
```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import operator

class WorkflowState(TypedDict):
    field: str
    accumulated: Annotated[list, operator.add]  # Auto-accumulates

# Create graph
workflow = StateGraph(WorkflowState)
workflow.add_node("process", process_node)
workflow.add_edge(START, "process")
workflow.add_edge("process", END)

# Compile
graph = workflow.compile()
```

**Frequency**: Used for all AI workflows (5+ graphs)

#### Conditional Edges with Send
```python
from langgraph.types import Send

def trigger_parallel(state: State, config: RunnableConfig) -> List[Send]:
    """Trigger parallel processing for multiple items."""
    return [
        Send("process_item", {"item": item})
        for item in state["items"]
    ]

workflow.add_conditional_edges(
    "prepare", trigger_parallel, ["process_item"]
)
```

**Frequency**: Used for parallel processing workflows (3+ occurrences)

### Domain Model Patterns

#### Base Model with Table Name
```python
from open_notebook.domain.base import ObjectModel
from typing import ClassVar, Optional

class Entity(ObjectModel):
    table_name: ClassVar[str] = "entity"
    field: str
    optional_field: Optional[str] = None
    
    @field_validator("field")
    @classmethod
    def validate_field(cls, v):
        if not v.strip():
            raise InvalidInputError("Field cannot be empty")
        return v
```

**Frequency**: All domain models follow this pattern (10+ models)

#### Relationship Management
```python
async def add_to_parent(self, parent_id: str) -> Any:
    """Create relationship edge in graph database."""
    if not parent_id:
        raise InvalidInputError("Parent ID must be provided")
    return await self.relate("relationship_name", parent_id)
```

**Frequency**: Used for all entity relationships (15+ occurrences)

#### Vectorization Pattern
```python
async def vectorize(self) -> None:
    """Vectorize content for semantic search."""
    EMBEDDING_MODEL = await model_manager.get_embedding_model()
    chunks = split_text(self.full_text)
    
    # Process chunks concurrently
    async def process_chunk(idx: int, chunk: str):
        embedding = (await EMBEDDING_MODEL.aembed([chunk]))[0]
        return (idx, embedding, chunk)
    
    tasks = [process_chunk(i, c) for i, c in enumerate(chunks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Atomic database transaction
    async with db_connection() as db:
        await db.query("BEGIN TRANSACTION")
        try:
            await db.query("DELETE embeddings WHERE source = $id", {"id": self.id})
            for idx, embedding, content in results:
                await db.query("CREATE embedding CONTENT {...}", {...})
            await db.query("COMMIT")
        except Exception:
            await db.query("ROLLBACK")
            raise
```

**Frequency**: Used for all vectorizable content (3+ models)

### React Query Patterns

#### Custom Hook with Mutations
```typescript
export function useCreateEntity() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateRequest) => api.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.entities })
      toast({ title: 'Success', description: 'Entity created' })
    },
    onError: () => {
      toast({ title: 'Error', variant: 'destructive' })
    },
  })
}
```

**Frequency**: Standard pattern for all mutations (20+ hooks)

#### Parallel Queries with useQueries
```typescript
const queries = useQueries({
  queries: items.map((item) => ({
    queryKey: QUERY_KEYS.item(item.id),
    queryFn: () => api.get(item.id),
    enabled: shouldFetch,
  })),
})

const dataByItem = useMemo(() => {
  const map: Record<string, Data> = {}
  items.forEach((item, index) => {
    map[item.id] = queries[index]?.data ?? []
  })
  return map
}, [items, queries])
```

**Frequency**: Used for fetching related data in parallel (5+ occurrences)

### Transaction Patterns

#### Database Transactions
```python
async with db_connection() as db:
    await db.query("BEGIN TRANSACTION")
    try:
        # Multiple operations
        await db.query("DELETE ...")
        await db.query("CREATE ...")
        await db.query("COMMIT")
    except Exception as e:
        await db.query("ROLLBACK")
        logger.error(f"Transaction failed: {e}")
        raise
```

**Frequency**: Used for atomic multi-step operations (5+ occurrences)

### Validation Patterns

#### Pydantic Field Validators
```python
from pydantic import field_validator

@field_validator("field")
@classmethod
from pydantic import field_validator

@field_validator("field")
@classmethod
def validate_field(cls, v):
    if not v or not v.strip():
        raise InvalidInputError("Field cannot be empty")
    return v

@field_validator("id", mode="before")
@classmethod
def parse_id(cls, value):
    """Parse id to handle RecordID and string inputs."""
    if value is None:
        return None
    return str(value) if value else None
```

**Frequency**: Used in all domain models with validation needs (15+ models)

## Best Practices Summary

1. **Always use type hints** in Python and TypeScript
2. **Handle errors explicitly** with proper logging and user feedback
3. **Use async/await** for all I/O operations
4. **Validate input** at API boundaries and domain models
5. **Clean up resources** in finally blocks or context managers
6. **Use dependency injection** for testability
7. **Memoize expensive operations** in React
8. **Follow repository pattern** for database access
9. **Use background jobs** for long-running operations
10. **Test with mocks** to isolate units
11. **Use transactions** for atomic multi-step database operations
12. **Process concurrently** with semaphores for rate limiting
13. **Invalidate queries** after mutations in React Query
14. **Use LangGraph** for complex AI workflows with state management
