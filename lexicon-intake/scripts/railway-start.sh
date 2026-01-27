#!/bin/bash

# Railway startup script for Lexicon Intake System

echo "🚀 Starting Lexicon Intake System on Railway..."

# Set environment variables for Railway
export PYTHONPATH="/app:$PYTHONPATH"

# Run database migrations first
echo "📊 Running database migrations..."
alembic upgrade head

# Check if this is web or worker service
if [ "$1" = "web" ]; then
    echo "🌐 Starting web service..."
    exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
elif [ "$1" = "worker" ]; then
    echo "⚙️ Starting worker service..."
    exec python -m app.workers
else
    echo "❌ Unknown service type: $1"
    echo "Usage: $0 [web|worker]"
    exit 1
fi
