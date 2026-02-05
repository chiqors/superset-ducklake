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
# In-memory DuckDB (ephemeral)
superset set_database_uri -d DuckDB-memory -u "duckdb:///:memory:" || true

# DuckLake (In-Memory with Hook)
# We use :memory: to avoid file locking issues with multiple Gunicorn workers
# The connection hook in superset_config.py will attach the persistent DuckLake
superset set_database_uri -d "DuckLake Analytics" -u "duckdb:///:memory:?allow_unsigned_extensions=true" || true

echo "Configuring DuckLake permissions (DML/CTAS)..."
python3 /app/docker/configure_superset_db.py "DuckLake Analytics" || echo "Failed to configure DuckLake permissions"

echo "Starting Gunicorn..."
gunicorn -w 4 -k sync --timeout 300 -b 0.0.0.0:8088 "superset.app:create_app()"
