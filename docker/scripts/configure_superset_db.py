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
        
        found_duck = False
        for database in dbs:
            print(f"Checking DB: '{database.database_name}' (URI: {database.sqlalchemy_uri})")
            
            # Check if it is a DuckDB database (either by name or URI)
            is_duck = "duck" in database.database_name.lower() or "duckdb" in str(database.sqlalchemy_uri).lower()
            
            if is_duck:
                found_duck = True
                print(f"-> identified as DuckDB-related. Checking permissions...")
                changed = False
                
                # Enable SQL Lab exposure
                if not database.expose_in_sqllab:
                    database.expose_in_sqllab = True
                    print(f"  - Enabled expose_in_sqllab for {database.database_name}")
                    changed = True

                # Enable CTAS (Create Table As Select)
                if not database.allow_ctas:
                    database.allow_ctas = True
                    print(f"  - Enabled allow_ctas for {database.database_name}")
                    changed = True
                    
                # Enable CVAS (Create View As Select)
                if not database.allow_cvas:
                    database.allow_cvas = True
                    print(f"  - Enabled allow_cvas for {database.database_name}")
                    changed = True
                    
                # Enable DML (Data Manipulation Language - INSERT/UPDATE/DELETE)
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
        
        if not found_duck:
            print("Warning: No DuckDB databases found to configure.")

if __name__ == "__main__":
    configure_all_duckdb()
