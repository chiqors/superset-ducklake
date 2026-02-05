FROM postgres:16-alpine
COPY scripts/psql-multiple-postgres.sh /docker-entrypoint-initdb.d/