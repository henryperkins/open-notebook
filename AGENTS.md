# Repository Guidelines

## Project Structure & Module Organization
Open Notebook pairs a SurrealDB-backed FastAPI service with a Next.js 15 frontend. Key directories:
- `api/`: FastAPI entrypoint, routers, and service wrappers that orchestrate domain objects.
- `open_notebook/`: core domain models, LangGraph workflows, and SurrealDB repository helpers.
- `commands/`: asynchronous jobs registered with `surreal-commands-worker` (batch uploads, source processing, podcasts).
- `frontend/`: React 19 app (`src/app`, `src/components`, `src/lib`) with Tailwind 4, Radix UI, and TanStack Query.
- `docs/` & `setup_guide/`: architecture, deployment, and onboarding references—update alongside feature or config shifts.

## Build, Test, and Development Commands
Run from the repo root:
- `uv sync && uv run run_api.py`: install Python deps and start the API on port 5055; migrations execute during startup.
- `uv run --env-file .env surreal-commands-worker --import-modules commands`: launch the background worker that executes registered commands.
- `make start-all`: spin up SurrealDB, API, worker, and frontend for an integrated smoke test (requires Docker).
- `cd frontend && npm run dev` (or `npm run build`): serve or compile the Next.js dashboard at http://localhost:3000.
- `uv run pytest` and `make lint` (`uv run python -m mypy .`): run backend tests and static analysis before committing; use `-k` to scope failing suites.

## Coding Style & Naming Conventions
- Python: 4-space indentation, 88-char line length (enforced by Ruff/Mypy). Stick to snake_case for functions/vars, PascalCase for classes, and include async signatures where IO occurs.
- Frontend: prefer colocated module directories, PascalCase components, camelCase hooks/utilities, and keep shared types in `frontend/src/lib/types`.
- Formatting: run `ruff check . --fix`, `uv run python -m mypy .`, and `npm run lint` until clean; document justified ignores inline.

## Testing Guidelines
- Extend pytest suites under `tests/` (e.g., `tests/test_models_api.py`) and reuse fixtures that disable password auth (`tests/conftest.py`).
- Mock SurrealDB access via `open_notebook.database.repository` helpers to keep tests deterministic.
- Validate LangGraph or command flows with targeted async tests and capture manual verification steps in PRs if automation is impractical.

## Commit & Pull Request Guidelines
- Write imperative, sub-72 character commit subjects (e.g., `Handle openai-compatible env matrix`) and squash noise before review.
- PRs must describe context, solution, and verification (commands, screenshots, recordings); call out migration impacts or env var additions early.
- Confirm linting, tests, and—when relevant—`make start-all` passes prior to requesting review; document residual risks or follow-up tasks.

## Security & Configuration Tips
- Set `SESSION_SECRET_KEY`, `OPEN_NOTEBOOK_PASSWORD`, and SurrealDB credentials via `.env`/`docker.env`; never commit secrets.
- Update `docs/deployment` when ports, env vars, or Compose profiles change so operators remain aligned.
- Keep LangGraph checkpoint files and uploaded assets inside `data/` to avoid leaking user content into the repo.
