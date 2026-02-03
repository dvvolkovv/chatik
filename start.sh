#!/bin/bash
set -e

echo "🚀 Starting AI Chat Backend..."
echo "📊 Environment: $APP_ENV"
echo "🔌 Port: $PORT"

# Run migrations
echo "📦 Running database migrations..."
alembic upgrade head
echo "✅ Migrations completed!"

# Start application
echo "🎯 Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
