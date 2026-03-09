#!/bin/bash
set -e

echo "=== Moonjar PMS Startup ==="

# Run Alembic migrations (if available)
echo "Running database migrations..."
if python -m alembic upgrade head; then
    echo "Migrations completed successfully"
else
    echo "WARNING: Migrations failed — continuing with existing schema"
fi

# Start the application
echo "Starting uvicorn..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
