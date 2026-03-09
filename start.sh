#!/bin/bash
set -e

echo "=== Moonjar PMS Startup ==="
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
echo "Python: $(python --version 2>&1)"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# Run Alembic migrations
echo ""
echo "=== Running database migrations ==="
if python -m alembic upgrade head 2>&1; then
    echo "=== Migrations completed successfully ==="
else
    echo "=== WARNING: Migrations FAILED (exit code $?) ==="
    echo "Attempting to show current alembic state..."
    python -m alembic current 2>&1 || true
    echo "=== Continuing with existing schema ==="
fi

# Start the application
echo ""
echo "=== Starting uvicorn ==="
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
