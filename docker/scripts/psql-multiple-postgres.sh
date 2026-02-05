#!/bin/bash

# credits: https://github.com/mrts/docker-postgresql-multiple-databases/blob/master/create-multiple-postgresql-databases.sh

set -e
set -u

function create_user_and_database() {
	local database=$1
	echo "  Creating user and database '$database'"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	    DO \$\$
	    BEGIN
	        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$database') THEN
	            CREATE USER $database WITH PASSWORD '$database';
	        END IF;
	    END
	    \$\$;
EOSQL
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$database'" | grep -q 1 || psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE $database"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "GRANT ALL PRIVILEGES ON DATABASE $database TO $database"
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
	echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
		create_user_and_database $db
	done
	echo "Multiple databases created"
fi

# Explicitly create ducklake_analytics database owned by the main user (superset)
# This avoids creating a separate 'ducklake_analytics' user
DATABASE="${POSTGRES_DUCKLAKE_DB:-ducklake_analytics}"
echo "  Creating database '$DATABASE' owned by '$POSTGRES_USER'"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DATABASE'" | grep -q 1 || psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE $DATABASE OWNER $POSTGRES_USER"
