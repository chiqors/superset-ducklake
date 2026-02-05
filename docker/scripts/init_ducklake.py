import duckdb
import os
import sys

DB_PATH = ':memory:'

# Define connection parameters from environment variables
PG_USER = os.environ.get('POSTGRES_DUCKLAKE_USER', 'superset')
PG_PASS = os.environ.get('POSTGRES_DUCKLAKE_PASSWORD', 'superset')
PG_HOST = os.environ.get('POSTGRES_DUCKLAKE_HOST', 'postgres')
PG_PORT = os.environ.get('POSTGRES_DUCKLAKE_PORT', '5432')
PG_DB = os.environ.get('POSTGRES_DUCKLAKE_DB', 'ducklake_analytics')

# GCS Credentials from environment variables
DUCKLAKE_STORAGE_DRIVER = os.environ.get("DUCKLAKE_STORAGE_DRIVER", "gcs").lower()

GCS_KEY_ID = os.environ.get('GCS_KEY_ID')
GCS_SECRET = os.environ.get('GCS_SECRET')
GCS_BUCKET_PATH = os.environ.get('GCS_BUCKET_PATH') or os.environ.get('GCS_DATA_PATH')

# S3 / MinIO Configuration
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
S3_BUCKET_PATH = os.environ.get("S3_BUCKET_PATH")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_URL_STYLE = os.environ.get("S3_URL_STYLE", "path")
S3_USE_SSL = os.environ.get("S3_USE_SSL", "true")

# BigQuery Configuration
BIGQUERY_ENABLED = os.getenv('BIGQUERY_ENABLED', 'false').lower() == 'true'
BIGQUERY_PROJECT_ID = os.getenv('BIGQUERY_PROJECT_ID', '')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Validate required credentials based on driver
if DUCKLAKE_STORAGE_DRIVER == 'gcs':
    if not (GCS_KEY_ID and GCS_SECRET and GCS_BUCKET_PATH):
        print("Error: GCS storage driver selected but missing required variables (GCS_KEY_ID, GCS_SECRET, GCS_BUCKET_PATH).")
        sys.exit(1)
    DATA_PATH = GCS_BUCKET_PATH
elif DUCKLAKE_STORAGE_DRIVER == 's3':
    if not (S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY and S3_BUCKET_PATH):
        print("Error: S3 storage driver selected but missing required variables (S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_PATH).")
        sys.exit(1)
    DATA_PATH = S3_BUCKET_PATH
else:
    print(f"Error: Invalid storage driver '{DUCKLAKE_STORAGE_DRIVER}'. Use 'gcs' or 's3'.")
    sys.exit(1)

# Construct Postgres connection string (libpq format)
pg_conn_str = f"dbname={PG_DB} user={PG_USER} password={PG_PASS} host={PG_HOST} port={PG_PORT}"

print(f"Initializing DuckLake DB at {DB_PATH} with driver: {DUCKLAKE_STORAGE_DRIVER}...")

try:
    # Allow unsigned extensions just in case
    con = duckdb.connect(DB_PATH, config={'allow_unsigned_extensions': 'true'})
    
    # Install and Load Extensions
    print("Installing and loading extensions...")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL postgres; LOAD postgres;")
    
    try:
        con.execute("INSTALL ducklake; LOAD ducklake;")
        print("DuckLake extension loaded.")
    except Exception as e:
        print(f"Warning: Failed to load ducklake extension: {e}")
    
    # Install and load BigQuery extension if enabled
    if BIGQUERY_ENABLED:
        print("Installing BigQuery extension...")
        con.execute("INSTALL bigquery FROM community;")
        con.execute("LOAD bigquery;")
        print("BigQuery extension loaded successfully")
    
    # Create GCS Secret (always create if vars exist, regardless of driver, for flexibility)
    if GCS_KEY_ID and GCS_SECRET:
        print("Creating GCS secret...")
        con.execute("DROP SECRET IF EXISTS gcs_secret")
        con.execute(f"""
        CREATE PERSISTENT SECRET gcs_secret (
            TYPE GCS,
            KEY_ID '{GCS_KEY_ID}',
            SECRET '{GCS_SECRET}'
        );
        """)

    # Create S3 Secret (always create if vars exist)
    if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
        print("Creating S3 secret...")
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
        
        con.execute("DROP SECRET IF EXISTS s3_secret")
        con.execute(f"""
        CREATE PERSISTENT SECRET s3_secret (
            {', '.join(s3_secret_params)}
        );
        """)
    
    # Create BigQuery attachment if enabled
    if BIGQUERY_ENABLED and BIGQUERY_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS:
        print(f"Attaching BigQuery project: {BIGQUERY_PROJECT_ID}")
        
        # Verify service account file exists
        if os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
            # Use ATTACH to connect entire BigQuery project (all datasets)
            attach_sql = f"""
            ATTACH 'project={BIGQUERY_PROJECT_ID}' as bq (TYPE bigquery, READ_ONLY);
            """
            try:
                con.execute(attach_sql)
                print(f"BigQuery project '{BIGQUERY_PROJECT_ID}' attached successfully as 'bq'")
                print("All datasets in the project are now accessible via bq.dataset_name.table_name")
                
                # Show available tables across all datasets
                try:
                    result = con.execute("SHOW ALL TABLES;").fetchall()
                    if result:
                        print(f"Found {len(result)} tables across all datasets")
                except Exception as e:
                    print(f"Note: Could not list tables: {e}")
                    
            except Exception as e:
                print(f"Warning: Could not attach BigQuery project: {e}")
        else:
            print(f"Warning: Service account file not found at {GOOGLE_APPLICATION_CREDENTIALS}")
    elif BIGQUERY_ENABLED:
        print("Warning: BigQuery enabled but PROJECT_ID or GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print("Verifying secret existence...")
    secrets = con.execute("SELECT * FROM duckdb_secrets()").fetchall()
    print(f"Secrets found: {secrets}")
    
    # Attach DuckLake
    if DATA_PATH:
        print(f"Attaching DuckLake using path: {DATA_PATH}...")
        try:
            # Check if already attached
            dbs = con.execute("SELECT database_name FROM duckdb_databases() WHERE database_name = 'ducklake'").fetchall()
            if not dbs:
                con.execute(f"ATTACH 'ducklake:postgres:{pg_conn_str}' AS ducklake (DATA_PATH '{DATA_PATH}')")
                print("Attached successfully.")
            else:
                print("Already attached.")
                
        except Exception as e:
            print(f"Error attaching ducklake: {e}")
    else:
        print("Warning: DATA_PATH not set. DuckLake not attached.")

    con.close()
    print("Initialization complete.")

except Exception as e:
    print(f"Critical error: {e}")
    sys.exit(1)
