# Open Notebook - Project Structure

## Architecture Overview
Open Notebook follows a modern full-stack architecture with clear separation between frontend, backend API, and core business logic.

**Stack**: Python (FastAPI) backend + Next.js/React frontend + SurrealDB database

## Directory Structure

### `/api` - REST API Layer
FastAPI-based REST API providing all backend functionality.

- **`/routers`**: API endpoint definitions organized by domain
  - `auth.py`, `oauth.py` - Authentication and OAuth integration
  - `notebooks.py`, `sources.py`, `notes.py` - Core content management
  - `chat.py`, `source_chat.py` - AI conversation endpoints
  - `podcasts.py`, `episode_profiles.py`, `speaker_profiles.py` - Podcast generation
  - `transformations.py` - Content transformation actions
  - `models.py`, `settings.py`, `config.py` - Configuration management
  - `search.py`, `embedding.py` - Search and vector operations
  - `batch_uploads.py`, `google_drive.py` - File upload and integrations
  - `context.py`, `insights.py` - Context management and AI insights
  - `commands.py` - Background job management

- **`/services`**: Business logic for API endpoints
  - Service files mirror router structure (e.g., `notebook_service.py`, `chat_service.py`)
  - `batch_upload_service.py`, `google_drive_service.py`, `oauth_service.py` - Integration services

- **Core files**:
  - `main.py` - FastAPI application entry point
  - `models.py` - Pydantic models for API requests/responses
  - `auth.py` - Authentication middleware
  - `client.py` - External API client utilities

### `/open_notebook` - Core Business Logic
Python package containing domain models, database operations, and AI workflows.

- **`/domain`**: Domain models and business entities
  - `base.py` - Base model classes
  - `notebook.py`, `podcast.py`, `transformation.py` - Core domain models
  - `models.py` - AI model configurations
  - `content_settings.py` - Content processing settings
  - `batch.py` - Batch operation models

- **`/database`**: Database layer
  - `repository.py` - SurrealDB repository pattern implementation
  - `migrate.py`, `async_migrate.py` - Database migration utilities

- **`/graphs`**: LangGraph-based AI workflows
  - `chat.py`, `source_chat.py` - Chat conversation graphs
  - `ask.py` - Question-answering workflow
  - `source.py` - Source content processing
  - `transformation.py` - Content transformation workflows
  - `tools.py` - LangChain tools for AI agents
  - `prompt.py` - Prompt management
  - `utils.py` - Graph utilities

- **`/services`**: Core services
  - `google_drive_service.py` - Google Drive integration
  - `session_service.py` - Session management

- **`/utils`**: Utility functions
  - `context_builder.py` - Context construction for AI
  - `text_utils.py`, `token_utils.py` - Text and token processing
  - `version_utils.py` - Version management

- **`/config`**: Configuration
  - `oauth_providers.py` - OAuth provider configurations

- **Core files**:
  - `config.py` - Application configuration
  - `exceptions.py` - Custom exceptions

### `/frontend` - Next.js Frontend
Modern React-based user interface.

- **`/src/app`**: Next.js app router pages and layouts
- **`/src/components`**: React components organized by feature
  - UI components for notebooks, sources, notes, chat, podcasts
- **`/src/lib`**: Frontend utilities and API client
- **Configuration**: `next.config.ts`, `tailwind.config.ts`, `tsconfig.json`

### `/commands` - Background Jobs
Surreal-commands based background job processors.

- `batch_commands.py` - Batch processing jobs
- `embedding_commands.py` - Vector embedding generation
- `podcast_commands.py` - Podcast generation jobs
- `source_commands.py` - Source content processing
- `example_commands.py` - Example job implementations

### `/migrations` - Database Migrations
SurrealQL migration files for database schema evolution.
- Numbered migration files (1.surrealql, 2.surrealql, etc.)
- Corresponding rollback files (*_down.surrealql)

### `/prompts` - AI Prompt Templates
Jinja2 templates for AI interactions.

- **`/ask`**: Question-answering prompts
- **`/podcast`**: Podcast generation prompts
- `chat.jinja`, `source_chat.jinja` - Chat conversation prompts

### `/tests` - Test Suite
Pytest-based test suite.

- `test_domain.py` - Domain model tests
- `test_graphs.py` - AI workflow tests
- `test_models_api.py` - API endpoint tests
- `test_oauth_api.py` - OAuth integration tests
- `test_utils.py` - Utility function tests
- `conftest.py` - Pytest configuration and fixtures

### `/docs` - Documentation
Comprehensive markdown documentation.

- **`/getting-started`**: Installation and quick start guides
- **`/user-guide`**: Feature documentation for end users
- **`/features`**: Detailed feature explanations
- **`/deployment`**: Deployment guides (Docker, reverse proxy, security)
- **`/development`**: Developer documentation and API reference
- **`/troubleshooting`**: Common issues and debugging

### `/scripts` - Utility Scripts
- `start-all.sh` - Development environment startup script
- `export_docs.py` - Documentation export utility

### Configuration Files
- `pyproject.toml` - Python project configuration and dependencies
- `Makefile` - Build and deployment automation
- `docker-compose.yml` - Docker orchestration (multiple variants)
- `Dockerfile`, `Dockerfile.single` - Container definitions
- `supervisord.conf` - Process management for containers
- `.env` - Environment variables (not in git)

## Key Architectural Patterns

### Layered Architecture
1. **API Layer** (`/api`): HTTP endpoints and request/response handling
2. **Service Layer** (`/api/services`, `/open_notebook/services`): Business logic
3. **Domain Layer** (`/open_notebook/domain`): Core business entities
4. **Data Layer** (`/open_notebook/database`): Database operations

### Background Processing
- Surreal-commands for async job processing
- Commands defined in `/commands` directory
- Jobs triggered via API and processed by worker

### AI Workflow Management
- LangGraph for complex AI workflows
- Modular graph definitions in `/open_notebook/graphs`
- Prompt templates in `/prompts` directory

### Multi-Provider AI Support
- Esperanto library for AI provider abstraction
- Configuration-driven model selection
- Support for 16+ AI providers

### AI Workflow Architecture
- **LangGraph Workflows**: Stateful AI agent workflows in `/open_notebook/graphs`
  - `source.py` - Source content processing pipeline
  - `chat.py`, `source_chat.py` - Conversational AI workflows
  - `transformation.py` - Content transformation workflows
  - `ask.py` - Question-answering workflow
- **State Management**: TypedDict-based state with annotated accumulators
- **Parallel Processing**: Conditional edges with Send for concurrent operations
- **Checkpointing**: SQLite-based conversation state persistence

### Domain-Driven Design
- **Base Model Pattern**: All domain models extend ObjectModel
- **Table Name Convention**: ClassVar table_name for database mapping
- **Relationship Edges**: Graph database relationships via relate() method
- **Validation**: Pydantic field_validator for input validation
- **Vectorization**: Built-in support for semantic search embeddings
