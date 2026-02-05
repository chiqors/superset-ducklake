#!/bin/bash
set -e

echo "Starting Superset initialization..."

# Run DB upgrade
echo "Running db upgrade..."
superset db upgrade

# Create admin user
if ! superset fab list-users | grep -q "^${ADMIN_USERNAME}\b"; then
    echo "Creating admin user..."
    superset fab create-admin --username "${ADMIN_USERNAME}" --firstname Superset --lastname Admin --email "${ADMIN_EMAIL}" --password "${ADMIN_PASSWORD}"
fi

# Init superset
echo "Initializing superset..."
superset init

# Initialize DuckLake
echo "Initializing DuckLake..."
python3 /app/docker/init_ducklake.py || echo "DuckLake initialization failed, skipping..."

# Configure Databases
echo "Configuring databases..."

# DuckLake (In-Memory with Hook)
# We use :memory: to avoid file locking issues with multiple Gunicorn workers
# The connection hook in superset_config.py will attach the persistent DuckLake
superset set_database_uri -d "DuckLake Analytics" -u "duckdb:///:memory:?allow_unsigned_extensions=true" || true

# DuckLake Metadata (Postgres)
# This allows browsing the DuckLake metadata directly in Superset via Postgres
DUCKLAKE_PG_URI="postgresql://${POSTGRES_DUCKLAKE_USER:-superset}:${POSTGRES_DUCKLAKE_PASSWORD:-superset}@${POSTGRES_DUCKLAKE_HOST:-postgres}:${POSTGRES_DUCKLAKE_PORT:-5432}/${POSTGRES_DUCKLAKE_DB:-ducklake_analytics}"
superset set_database_uri -d "DuckLake Metadata" -u "$DUCKLAKE_PG_URI" || true

echo "Configuring DuckLake permissions (DML/CTAS)..."
python3 /app/docker/configure_superset_db.py || echo "Failed to configure DuckLake permissions"

echo "Starting Gunicorn..."
# High performance configuration:
# - k gevent: Async workers for I/O bound apps
# - w 10: Number of workers (adjust based on CPU cores, e.g., 2 x cores + 1)
# - worker-connections 1000: Max simultaneous connections per worker

WORKER_CLASS=${GUNICORN_WORKER_CLASS:-gevent}
WORKERS=${GUNICORN_WORKERS:-10}
TIMEOUT=${GUNICORN_TIMEOUT:-120}

gunicorn -w $WORKERS -k $WORKER_CLASS --worker-connections 1000 --timeout $TIMEOUT -b 0.0.0.0:8088 "superset.app:create_app()"
