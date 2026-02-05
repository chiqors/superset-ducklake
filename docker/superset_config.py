import os
from sqlalchemy import event
from sqlalchemy.engine import Engine

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]

# DuckLake Configuration
GCS_KEY_ID = os.environ.get("GCS_KEY_ID")
GCS_SECRET = os.environ.get("GCS_SECRET")
GCS_DATA_PATH = os.environ.get("GCS_DATA_PATH")
PG_USER = os.environ.get("POSTGRES_USER", "superset")
PG_PASS = os.environ.get("POSTGRES_PASSWORD", "superset")
PG_HOST = "postgres"
PG_PORT = "5432"
PG_DB = os.environ.get("POSTGRES_DB", "ducklake_analytics")

@event.listens_for(Engine, "connect")
def ducklake_connect(dbapi_connection, connection_record):
    try:
        # Check if it is a DuckDB connection
        conn_type = str(type(dbapi_connection)).lower()
        if "duckdb" in conn_type:
            cursor = dbapi_connection.cursor()
            try:
                # Check if this is the DuckLake Analytics connection
                # We can't easily check the DB name here, but we can check if environment vars are present.
                # Since we want to enable DuckLake for ANY DuckDB connection in this container (simplest approach),
                # we proceed.
                
                if GCS_DATA_PATH and PG_DB and GCS_KEY_ID and GCS_SECRET:
                    # Construct Postgres connection string in Key-Value format (libpq style)
                    # This is more robust for the postgres extension when used with DuckLake
                    pg_conn_str = f"dbname={PG_DB} user={PG_USER} password={PG_PASS} host={PG_HOST} port={PG_PORT}"
                    
                    # 1. Install and Load Extensions
                    cursor.execute("INSTALL httpfs")
                    cursor.execute("LOAD httpfs")
                    cursor.execute("INSTALL postgres")
                    cursor.execute("LOAD postgres")
                    cursor.execute("INSTALL ducklake")
                    cursor.execute("LOAD ducklake")
                    
                    # 2. Create GCS Secret (Required for In-Memory)
                    # Use CREATE SECRET (Idempotent check not strictly needed if we use CREATE OR REPLACE or just overwrite)
                    # DuckDB 0.10+ syntax:
                    cursor.execute("DROP SECRET IF EXISTS gcs_secret")
                    cursor.execute(f"""
                        CREATE SECRET gcs_secret (
                            TYPE GCS,
                            KEY_ID '{GCS_KEY_ID}',
                            SECRET '{GCS_SECRET}'
                        )
                    """)
                    
                    # 3. Attach DuckLake
                    # Use unique alias and explicit DATA_PATH option
                    cursor.execute(f"ATTACH 'ducklake:postgres:{pg_conn_str}' AS ducklake_analytics (DATA_PATH '{GCS_DATA_PATH}')")
                    
                    # 4. Set as default catalog
                    cursor.execute("USE ducklake_analytics")
                    
                    print(f"Successfully configured DuckLake for connection: {conn_type}")
            finally:
                # cursor.close() 
                pass
    except Exception as e:
        # Print error but don't crash, so standard DuckDB usage (if any) still works
        print(f"Error in DuckLake connection hook: {e}")
