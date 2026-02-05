# Create admin user.
docker exec -it superset superset fab create-admin \
    --username admin \
    --firstname Superset \
    --lastname Admin \
    --email admin@superset.com \
    --password admin

# Upgrade database to latest.
docker exec -it superset superset db upgrade

# Setup roles.
docker exec -it superset superset init

# Create database connection for DuckDB.
docker exec -it superset superset set_database_uri \
    -d DuckDB-memory \
    -u duckdb:///:memory: