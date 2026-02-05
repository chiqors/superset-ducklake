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
GCS_KEY_ID = os.environ.get('GCS_KEY_ID')
GCS_SECRET = os.environ.get('GCS_SECRET')
DATA_PATH = os.environ.get('GCS_DATA_PATH')

if not all([GCS_KEY_ID, GCS_SECRET, DATA_PATH]):
    print("Error: Missing required environment variables (GCS_KEY_ID, GCS_SECRET, GCS_DATA_PATH).")
    print("Please set them in docker-compose.yml")
    sys.exit(1)

# Construct ATTACH URL
attach_url = f"ducklake:postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}?data_path={DATA_PATH}"

print(f"Initializing DuckLake DB at {DB_PATH}...")

try:
    # Allow unsigned extensions just in case
    con = duckdb.connect(DB_PATH, config={'allow_unsigned_extensions': 'true'})
    
    # Install and Load Extensions
    print("Installing and loading extensions...")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    try:
        con.execute("INSTALL ducklake; LOAD ducklake;")
        print("DuckLake extension loaded.")
    except Exception as e:
        print(f"Warning: Failed to load ducklake extension: {e}")
    
    # Create Secret
    print("Creating GCS secret...")
    # Drop secret if exists to ensure update
    con.execute("DROP SECRET IF EXISTS gcs_secret")
    con.execute(f"""
    CREATE PERSISTENT SECRET gcs_secret (
        TYPE GCS,
        KEY_ID '{GCS_KEY_ID}',
        SECRET '{GCS_SECRET}'
    );
    """)
    
    print("Verifying secret existence...")
    secrets = con.execute("SELECT * FROM duckdb_secrets()").fetchall()
    print(f"Secrets found: {secrets}")
    
    # Attach Database
    print(f"Attaching DuckLake with URL: {attach_url}")
    try:
        # Check if already attached
        dbs = con.execute("SELECT database_name FROM duckdb_databases() WHERE database_name = 'ducklake'").fetchall()
        if not dbs:
            con.execute(f"ATTACH '{attach_url}' AS ducklake")
            print("Attached successfully.")
        else:
            print("Already attached.")
            
    except Exception as e:
        print(f"Error attaching ducklake: {e}")

    con.close()
    print("Initialization complete.")

except Exception as e:
    print(f"Critical error: {e}")
    sys.exit(1)
