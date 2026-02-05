#!/bin/bash

# Load environment variables from .env if it exists
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/../../.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading configuration from .env..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set defaults if not provided in .env
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@superset.com}

echo "Using Admin User: $ADMIN_USERNAME"

# Create admin user.
docker exec -it superset superset fab create-admin \
    --username "$ADMIN_USERNAME" \
    --firstname Superset \
    --lastname Admin \
    --email "$ADMIN_EMAIL" \
    --password "$ADMIN_PASSWORD"

# Upgrade database to latest.
docker exec -it superset superset db upgrade

# Setup roles.
docker exec -it superset superset init

# Create database connection for DuckDB.
docker exec -it superset superset set_database_uri \
    -d DuckDB-memory \
    -u duckdb:///:memory:
