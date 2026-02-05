# Superset with DuckLake Integration

This repository contains a production-ready configuration for Apache Superset integrated with **DuckLake**. It enables a stateless analytics architecture where:
- **Compute**: DuckDB (running within Superset container)
- **Metadata**: PostgreSQL (persistent storage for DuckDB/DuckLake catalogs)
- **Data**: Google Cloud Storage (GCS) (parquet/iceberg files)

## Architecture

```mermaid
graph TD
    User[User] -->|SQL/UI| Superset
    Superset -->|DuckDB Engine| DuckDB[DuckDB (In-Memory)]
    DuckDB -->|Attach| Postgres[Postgres (Metadata Store)]
    DuckDB -->|Read/Write| GCS[Google Cloud Storage (Data Lake)]
    
    subgraph "Superset Container"
        Superset
        DuckDB
    end
    
    subgraph "Persistence Layer"
        Postgres
        GCS
    end
```

### Key Features
- **Stateless Application**: No analytic data is stored in the Superset container.
- **Persistent Metadata**: DuckLake catalogs are stored in the `ducklake_analytics` PostgreSQL database.
- **Secure Credentials**: GCS credentials are managed via environment variables and persistent DuckDB secrets.
- **Automated Setup**: Custom initialization scripts handle database creation, extension loading, and permission configuration.
- **Additional Drivers**: Pre-installed support for **BigQuery** and **Trino**.

## Prerequisites

- Docker & Docker Compose
- Google Cloud Storage (GCS) Bucket and HMAC Keys (Access Key & Secret)

## Configuration

The setup is controlled via environment variables in `docker-compose.yml`.

### Essential Variables

| Variable | Description |
|----------|-------------|
| `GCS_KEY_ID` | GCS HMAC Access Key |
| `GCS_SECRET` | GCS HMAC Secret |
| `GCS_DATA_PATH` | Base GCS URI (e.g., `gs://my-analytics-bucket/`) |
| `POSTGRES_DB` | Name of the metadata database (default: `ducklake_analytics`) |

## Getting Started

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd superset
    ```

2.  **Update Credentials**:
    Edit `docker-compose.yml` and set your `GCS_KEY_ID` and `GCS_SECRET`.
    *(Recommended: Use a `.env` file for production credentials)*

3.  **Start Services**:
    ```bash
    docker compose up -d --build
    ```

4.  **Access Superset**:
    - URL: `http://localhost:8080`
    - Username: `admin`
    - Password: `admin`

5.  **Verify Connection**:
    - Go to **SQL Lab**.
    - Select Database: **DuckLake Analytics**.
    - Schema: `main` (or your specific schema).
    - You should see your GCS tables listed.

## Usage Guide

### Creating Tables (DDL)
You can create tables directly in SQL Lab. Metadata will be stored in Postgres, and data files will be written to GCS.

```sql
CREATE TABLE my_table AS SELECT * FROM 'gs://public-data/file.parquet';
```

### Handling Complex Types (STRUCT/LIST)
Superset's UI currently has limitations visualizing raw `STRUCT` or `LIST` types from DuckDB. If you encounter an error like *"An error occurred while expanding the table schema"*, follow this pattern:

**Create a View to flatten or cast complex types:**

```sql
CREATE VIEW my_view AS 
SELECT 
    id,
    name,
    CAST(complex_column AS JSON) as complex_column_json
FROM my_complex_table;
```

Then query `my_view` in Superset.

## Directory Structure

- `docker/`: Docker configuration and scripts.
  - `scripts/`: Initialization and configuration scripts.
  - `superset_config.py`: Superset Python configuration (hooks for DuckLake).
- `docker-compose.yml`: Service orchestration.

## Troubleshooting

- **"No such file or directory" during attach**: Ensure the Postgres service is healthy and the `POSTGRES_DB` exists (handled automatically by `psql-multiple-postgres.sh`).
- **Permission Denied**: Ensure `allow_dml`, `allow_ctas`, and `allow_cvas` are enabled for the database (handled automatically by `configure_superset_db.py`).
