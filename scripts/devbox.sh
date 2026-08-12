#!/usr/bin/env bash
set -e

echo "========================================================"
echo "🚀 Starting Havi Platform Devbox (One-Click Environment)"
echo "========================================================"

# 1. Start Docker Infrastructure (Postgres, Redis, MinIO)
echo "📦 [1/4] Starting Docker infrastructure (Postgres, Redis, MinIO)..."
docker compose up -d

# 2. Run Database Migrations
echo "🗄️ [2/4] Running database migrations..."
(cd apps/backend && uv run alembic upgrade head)

# Function to handle clean exit on Ctrl+C (SIGINT / SIGTERM)
cleanup() {
  echo ""
  echo "🛑 Stopping Havi services..."
  kill $(jobs -p) 2>/dev/null || true
  echo "👋 Devbox stopped cleanly."
  exit 0
}

trap cleanup INT TERM EXIT

# 3. Start Backend Services & Web Frontend
echo "⚡ [3/4] Starting Backend API (port 8000)..."
(cd apps/backend && uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000) &

echo "⚙️ [4/4] Starting Celery Worker & Beat..."
(cd apps/backend && uv run celery -A worker.celery_app:celery_app worker -l info) &
(cd apps/backend && uv run celery -A worker.celery_app:celery_app beat -l info) &

echo "🌐 Starting Next.js Web Frontend (port 3000)..."
(npm run dev:web) &

echo ""
echo "========================================================"
echo "✨ Havi Devbox is LIVE!"
echo "   - Web App:     http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs:    http://localhost:8000/docs"
echo "   Press Ctrl+C at any time to stop all services."
echo "========================================================"

wait
