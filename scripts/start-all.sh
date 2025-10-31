#!/bin/bash

# Cleanup function to stop all services
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."

    # Stop all processes
    pkill -f "run_api.py" 2>/dev/null || true
    pkill -f "surreal-commands-worker" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true

    # Stop Docker containers
    docker compose down 2>/dev/null || true

    echo "✅ All services stopped!"
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

echo "🚀 Starting Open Notebook (Database + API + Worker + Frontend)..."
echo "📊 Starting SurrealDB..."
docker compose up -d surrealdb

echo "🔧 Starting API backend..."
# Source .env file to load environment variables
set -a
source .env
set +a
uv run run_api.py &
API_PID=$!

sleep 3
echo "⚙️ Starting background worker..."
uv run --env-file .env surreal-commands-worker --import-modules commands &
WORKER_PID=$!

sleep 2
echo "🌐 Starting Next.js frontend..."
echo "✅ All services started!"
echo "📱 Frontend: http://localhost:3000"
echo "🔗 API: http://localhost:5055"
echo "📚 API Docs: http://localhost:5055/docs"
echo "Press Ctrl+C to stop all services..."

# Start frontend in the foreground
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for frontend process (this will be interrupted by Ctrl+C)
wait $FRONTEND_PID
