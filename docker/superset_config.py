import os
from sqlalchemy import event
from sqlalchemy.engine import Engine

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]

# ---------------------------------------------------------
# Performance & Scaling Configuration
# ---------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.environ.get("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.environ.get("REDIS_RESULTS_DB", "1")
REDIS_CACHE_DB = os.environ.get("REDIS_CACHE_DB", "2")

# Only configure Celery and Redis if REDIS_HOST is provided
if REDIS_HOST:
    # 1. Celery Config for Async Queries
    class CeleryConfig:
        broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
        imports = ("superset.sql_lab",)
        result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
        worker_prefetch_multiplier = 10
        task_acks_late = True
        task_annotations = {
            "sql_lab.get_sql_results": {
                "rate_limit": "100/s",
            },
        }

    CELERY_CONFIG = CeleryConfig

    # 2. Caching Config (Redis)
    CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 86400, # 1 day default
        "CACHE_KEY_PREFIX": "superset_cache_",
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": REDIS_CACHE_DB,
    }

    # Cache for query results
    DATA_CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 86400,
        "CACHE_KEY_PREFIX": "superset_data_",
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": REDIS_CACHE_DB,
    }

    # Cache for dashboard filter state
    FILTER_STATE_CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 86400,
        "CACHE_KEY_PREFIX": "superset_filter_",
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": REDIS_CACHE_DB,
    }

    # Cache for Explore form data
    EXPLORE_FORM_DATA_CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 86400,
        "CACHE_KEY_PREFIX": "superset_explore_",
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": REDIS_CACHE_DB,
    }

    # 3. Async Query Execution
    # Allow running queries asynchronously in SQL Lab
    SQL_LAB_ASYNC = True

else:
    # Fallback/Simple Configuration (No Redis)
    SQL_LAB_ASYNC = False
    
    # Use simple in-memory cache for development/simple mode
    CACHE_CONFIG = {
        "CACHE_TYPE": "SimpleCache"
    }

# 4. Row Limits & Performance
ROW_LIMIT = 50000
SQL_MAX_ROW = 1000000 # Allow larger result sets for analysts if needed
SUPERSET_WEBSERVER_TIMEOUT = 300

# ---------------------------------------------------------
# DuckLake Configuration
# ---------------------------------------------------------
DUCKLAKE_STORAGE_DRIVER = os.environ.get("DUCKLAKE_STORAGE_DRIVER", "gcs").lower()

GCS_KEY_ID = os.environ.get("GCS_KEY_ID")
GCS_SECRET = os.environ.get("GCS_SECRET")
# Support legacy GCS_DATA_PATH or new GCS_BUCKET_PATH
GCS_BUCKET_PATH = os.environ.get("GCS_BUCKET_PATH") or os.environ.get("GCS_DATA_PATH")

# S3 / MinIO Configuration
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
S3_BUCKET_PATH = os.environ.get("S3_BUCKET_PATH")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_URL_STYLE = os.environ.get("S3_URL_STYLE", "path")
S3_USE_SSL = os.environ.get("S3_USE_SSL", "true")

PG_USER = os.environ.get("POSTGRES_DUCKLAKE_USER", "superset")
PG_PASS = os.environ.get("POSTGRES_DUCKLAKE_PASSWORD", "superset")
PG_HOST = os.environ.get("POSTGRES_DUCKLAKE_HOST", "postgres")
PG_PORT = os.environ.get("POSTGRES_DUCKLAKE_PORT", "5432")
PG_DB = os.environ.get("POSTGRES_DUCKLAKE_DB", "ducklake_analytics")
MOTHERDUCK_TOKEN = os.environ.get("MOTHERDUCK_TOKEN")

@event.listens_for(Engine, "connect")
def ducklake_connect(dbapi_connection, connection_record):
    try:
        # Check if it is a DuckDB connection
        conn_type = str(type(dbapi_connection)).lower()
        if "duckdb" in conn_type:
            cursor = dbapi_connection.cursor()
            try:
                # 0. Optional: MotherDuck Support
                if MOTHERDUCK_TOKEN:
                    try:
                        cursor.execute("INSTALL motherduck")
                        cursor.execute("LOAD motherduck")
                    except Exception as e:
                        print(f"Warning: Failed to load MotherDuck extension: {e}")

                # Check if this is the DuckLake Analytics connection
                
                # Determine DATA_PATH based on storage driver
                DATA_PATH = None
                if DUCKLAKE_STORAGE_DRIVER == "s3":
                    DATA_PATH = S3_BUCKET_PATH
                else:
                    DATA_PATH = GCS_BUCKET_PATH
                
                # 1. Install and Load Extensions
                cursor.execute("INSTALL httpfs")
                cursor.execute("LOAD httpfs")
                cursor.execute("INSTALL postgres")
                cursor.execute("LOAD postgres")
                cursor.execute("INSTALL ducklake")
                cursor.execute("LOAD ducklake")
                
                # 2. Create GCS Secret (if configured)
                if GCS_KEY_ID and GCS_SECRET:
                    cursor.execute("DROP SECRET IF EXISTS gcs_secret")
                    cursor.execute(f"""
                        CREATE SECRET gcs_secret (
                            TYPE GCS,
                            KEY_ID '{GCS_KEY_ID}',
                            SECRET '{GCS_SECRET}'
                        )
                    """)
                    
                # 3. Create S3 Secret (if configured)
                if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
                    # Construct S3 Secret parameters
                    s3_secret_params = [
                        "TYPE S3",
                        f"KEY_ID '{S3_ACCESS_KEY_ID}'",
                        f"SECRET '{S3_SECRET_ACCESS_KEY}'",
                        f"REGION '{S3_REGION}'",
                        f"URL_STYLE '{S3_URL_STYLE}'",
                        f"USE_SSL {S3_USE_SSL}"
                    ]
                    if S3_ENDPOINT:
                         s3_secret_params.append(f"ENDPOINT '{S3_ENDPOINT}'")
                         
                    cursor.execute("DROP SECRET IF EXISTS s3_secret")
                    cursor.execute(f"""
                        CREATE SECRET s3_secret (
                            {', '.join(s3_secret_params)}
                        )
                    """)

                # 4. Attach DuckLake (if DATA_PATH is available)
                if DATA_PATH and PG_DB:
                    # Construct Postgres connection string in Key-Value format (libpq style)
                    pg_conn_str = f"dbname={PG_DB} user={PG_USER} password={PG_PASS} host={PG_HOST} port={PG_PORT}"
                    
                    # Use unique alias and explicit DATA_PATH option
                    cursor.execute(f"ATTACH 'ducklake:postgres:{pg_conn_str}' AS ducklake_analytics (DATA_PATH '{DATA_PATH}')")
                    
                    # 5. Set as default catalog
                    cursor.execute("USE ducklake_analytics")
                    
                    print(f"Successfully configured DuckLake for connection: {conn_type} using driver: {DUCKLAKE_STORAGE_DRIVER}")
            finally:
                # cursor.close() 
                pass
    except Exception as e:
        # Print error but don't crash, so standard DuckDB usage (if any) still works
        print(f"Error in DuckLake connection hook: {e}")
