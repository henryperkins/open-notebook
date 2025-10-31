# Open Notebook - Technology Stack

## Programming Languages
- **Python 3.11+** (Backend, AI workflows, background jobs)
- **TypeScript/JavaScript** (Frontend with Next.js/React)
- **SurrealQL** (Database migrations)

## Backend Stack

### Core Framework
- **FastAPI** (0.104.0+) - Modern async web framework
- **Uvicorn** (0.24.0+) - ASGI server
- **Pydantic** (2.9.2+) - Data validation and settings management

### AI & LLM Integration
- **LangChain** (0.3.3+) - LLM application framework
- **LangGraph** (0.2.38+) - Stateful AI agent workflows
- **Esperanto** (2.8.0+) - Multi-provider AI abstraction layer
- **Provider-specific libraries**:
  - `langchain-openai` (0.2.3+)
  - `langchain-anthropic` (0.2.3+)
  - `langchain-ollama` (0.2.0+)
  - `langchain-google-genai` (2.1.10+)
  - `langchain-google-vertexai` (2.0.28+)
  - `langchain-groq` (0.2.1+)
  - `langchain_mistralai` (0.2.1+)
  - `langchain_deepseek` (0.1.3+)

### Content Processing
- **content-core** (1.0.2+) - Content extraction and processing
- **podcast-creator** (0.7.0+) - Podcast generation engine
- **ai-prompter** (0.3+) - Prompt management
- **tiktoken** (0.8.0+) - Token counting for OpenAI models

### Database & Storage
- **SurrealDB** (1.0.4+) - Multi-model database
- **surreal-commands** (1.0.13+) - Background job processing
- **langgraph-checkpoint-sqlite** (2.0.0+) - Conversation state persistence

### Authentication & Security
- **authlib** - OAuth integration
- **itsdangerous** (2.2.0+) - Secure token generation
- **Google OAuth libraries**:
  - `google-api-python-client`
  - `google-auth-httplib2`
  - `google-auth-oauthlib`

### Utilities
- **loguru** (0.7.2+) - Logging
- **python-dotenv** (1.0.1+) - Environment variable management
- **httpx[socks]** (0.27.0+) - HTTP client with proxy support
- **aiofiles** (25.1.0+) - Async file operations
- **psutil** (7.1.2+) - System monitoring

## Frontend Stack

### Core Framework
- **Next.js** (15.4.7) - React framework with App Router
- **React** (19.1.0) - UI library
- **TypeScript** (5.x) - Type safety

### UI Components & Styling
- **Radix UI** - Accessible component primitives
  - Dialog, Dropdown, Select, Tabs, Tooltip, and more
- **Tailwind CSS** (4.x) - Utility-first CSS framework
- **Lucide React** (0.525.0+) - Icon library
- **class-variance-authority** (0.7.1+) - Component variants
- **clsx** (2.1.1+) - Conditional classnames
- **tailwind-merge** (3.3.1+) - Tailwind class merging

### State Management & Data Fetching
- **Zustand** (5.0.6+) - Lightweight state management
- **TanStack Query** (5.83.0+) - Server state management
- **Axios** (1.12.0+) - HTTP client

### Form Handling
- **React Hook Form** (7.60.0+) - Form state management
- **@hookform/resolvers** (5.1.1+) - Form validation
- **Zod** (4.0.5+) - Schema validation

### Rich Content Editing
- **@uiw/react-md-editor** (4.0.8+) - Markdown editor
- **@monaco-editor/react** (4.7.0+) - Code editor
- **react-markdown** (10.1.0+) - Markdown rendering

### Additional Libraries
- **react-dropzone** (14.3.8+) - File upload
- **date-fns** (4.1.0+) - Date utilities
- **next-themes** (0.4.6+) - Theme management
- **sonner** (2.0.6+) - Toast notifications
- **use-debounce** (10.0.6+) - Debouncing utility
- **cmdk** (1.1.1+) - Command palette

## Development Tools

### Python Development
- **uv** - Fast Python package manager (used throughout project)
- **ruff** (0.5.5+) - Fast Python linter and formatter
- **mypy** (1.11.1+) - Static type checker
- **pytest** (8.0.0+) - Testing framework
- **pytest-asyncio** (1.2.0+) - Async test support
- **pre-commit** (4.1.0+) - Git hooks
- **ipykernel** (6.29.5+) - Jupyter notebook support

### Frontend Development
- **ESLint** (9.x) - JavaScript/TypeScript linting
- **eslint-config-next** (15.4.2) - Next.js ESLint configuration

### Containerization
- **Docker** - Container runtime
- **Docker Compose** - Multi-container orchestration
- **Supervisor** - Process management in containers

## Build System & Commands

### Python (via Makefile)
```bash
make api              # Start FastAPI backend
make worker           # Start background job worker
make database         # Start SurrealDB container
make start-all        # Start all services (DB, API, worker, frontend)
make stop-all         # Stop all services
make status           # Check service status
make lint             # Run mypy type checking
make ruff             # Run ruff linter
make clean-cache      # Clean Python cache files
```

### Frontend (via npm)
```bash
npm run dev           # Development server
npm run build         # Production build
npm run start         # Start production server
npm run lint          # Run ESLint
```

### Docker
```bash
make docker-push              # Build and push version tags
make docker-push-latest       # Update v1-latest tags
make docker-release           # Full release (version + latest)
make docker-buildx-prepare    # Setup multi-platform builder
make docker-buildx-clean      # Clean buildx builders
```

## Configuration Files

### Python
- `pyproject.toml` - Project metadata, dependencies, tool configuration
- `uv.lock` - Locked dependency versions
- `mypy.ini` - Type checker configuration
- `.python-version` - Python version specification

### Frontend
- `package.json` - Node dependencies and scripts
- `tsconfig.json` - TypeScript configuration
- `next.config.ts` - Next.js configuration
- `tailwind.config.ts` - Tailwind CSS configuration
- `eslint.config.mjs` - ESLint configuration

### Docker
- `Dockerfile` - Multi-container image
- `Dockerfile.single` - Single-container image with embedded SurrealDB
- `docker-compose.yml` - Standard deployment
- `docker-compose.dev.yml` - Development environment
- `docker-compose.full.yml` - Full stack with all services
- `docker-compose.single.yml` - Single container deployment
- `supervisord.conf` - Process management (multi-container)
- `supervisord.single.conf` - Process management (single-container)

### Environment
- `.env` - Environment variables (not in git)
- `docker.env` - Docker environment template

## Database
- **SurrealDB** - Multi-model database (document, graph, key-value)
- **Connection**: WebSocket (ws://localhost:8000/rpc)
- **Migrations**: Numbered SurrealQL files in `/migrations`

## External Dependencies
- **AI Providers**: OpenAI, Anthropic, Google (GenAI/Vertex), Groq, Ollama, Mistral, DeepSeek, xAI, OpenRouter, LM Studio
- **OAuth Providers**: Google Drive integration
- **Content Processing**: Docling (via content-core) for document parsing

## Key Design Patterns

### Backend Patterns
- **Repository Pattern**: Database abstraction via repo_query and domain models
- **Command Pattern**: Background jobs using surreal-commands decorator
- **State Machine**: LangGraph workflows for AI processing pipelines
- **Domain-Driven Design**: Rich domain models with business logic
- **Dependency Injection**: FastAPI Depends for service composition

### Frontend Patterns
- **Server State**: TanStack Query for API data caching and synchronization
- **Client State**: Zustand for lightweight global state
- **Compound Components**: Radix UI primitives for accessible components
- **Custom Hooks**: Encapsulated data fetching and mutation logic
- **Optimistic Updates**: Query invalidation after mutations

## Version Information
- **Current Version**: 1.1.1 (from pyproject.toml)
- **Python Requirement**: >=3.11, <3.13
- **Node.js**: Version 20+ recommended
- **Docker Images**: 
  - `lfnovo/open_notebook:v1-latest` (multi-container)
  - `lfnovo/open_notebook:v1-latest-single` (single-container)
  - `ghcr.io/lfnovo/open-notebook:v1-latest` (GitHub Container Registry)
