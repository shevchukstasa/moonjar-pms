#!/bin/bash
set -e

echo "=== Moonjar PMS Startup ==="
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
echo "Python: $(python --version 2>&1)"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# Ensure alembic_version.version_num is wide enough for long revision IDs (default VARCHAR(32))
python - <<'PYEOF'
import os, sys
try:
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
    cur.close()
    conn.close()
    print("alembic_version.version_num expanded to VARCHAR(128)")
except Exception as e:
    print(f"Note: could not expand alembic_version column: {e}", file=sys.stderr)
PYEOF

# Build frontend if not already built
FRONTEND_DIR="presentation/dashboard"
if [ -d "$FRONTEND_DIR" ]; then
    echo ""
    echo "=== Building frontend ==="
    if command -v node &> /dev/null; then
        cd "$FRONTEND_DIR"
        npm ci --prefer-offline 2>&1 | tail -3
        VITE_API_URL="" VITE_WS_URL="" \
        VITE_GOOGLE_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-}" \
        npm run build 2>&1
        echo "=== Frontend build complete ==="
        cd ../..
    else
        echo "=== WARNING: Node.js not found, skipping frontend build ==="
    fi
fi

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
