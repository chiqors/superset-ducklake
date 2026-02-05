import sys
from superset.app import create_app

def configure_all_duckdb():
    print("Creating Superset app context...")
    app = create_app()
    with app.app_context():
        # Imports must be inside the app context
        from superset import db
        from superset.models.core import Database
        
        print("Scanning all databases...")
        dbs = db.session.query(Database).all()
        
        for database in dbs:
            print(f"Checking DB: '{database.database_name}' (URI: {database.sqlalchemy_uri})")
            
            # Check if it is a DuckDB database (either by name or URI)
            is_duck = "duck" in database.database_name.lower() or "duckdb" in str(database.sqlalchemy_uri).lower()
            
            if is_duck:
                print(f"-> identified as DuckDB-related. Checking permissions...")
                changed = False
                
                if not database.allow_ctas:
                    database.allow_ctas = True
                    print(f"  - Enabled allow_ctas for {database.database_name}")
                    changed = True
                    
                if not database.allow_cvas:
                    database.allow_cvas = True
                    print(f"  - Enabled allow_cvas for {database.database_name}")
                    changed = True
                    
                if not database.allow_dml:
                    database.allow_dml = True
                    print(f"  - Enabled allow_dml for {database.database_name}")
                    changed = True
                
                if changed:
                    try:
                        db.session.commit()
                        print(f"  [SUCCESS] Updated configuration for {database.database_name}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"  [ERROR] Failed to update {database.database_name}: {e}")
                else:
                    print(f"  [OK] Configuration already correct for {database.database_name}")

if __name__ == "__main__":
    configure_all_duckdb()
