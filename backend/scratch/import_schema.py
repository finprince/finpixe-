import os
import re
from django.db import connection

def run_import():
    schema_path = r"d:\finpixe\AI-accounting-0.03\schema.sql"
    if not os.path.exists(schema_path):
        print(f"Error: {schema_path} does not exist.")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split statements by semicolon while ignoring comments if any
    raw_statements = content.split(";")
    
    statements = []
    for stmt in raw_statements:
        cleaned = stmt.strip()
        if cleaned:
            statements.append(cleaned)

    print(f"Total statements to execute: {len(statements)}")

    success_count = 0
    error_count = 0
    errors = []

    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';")
        
        for idx, stmt in enumerate(statements, 1):
            try:
                cursor.execute(stmt)
                success_count += 1
            except Exception as e:
                error_count += 1
                table_match = re.search(r"CREATE\s+TABLE\s+[`]?(\w+)[`]?", stmt, re.IGNORECASE)
                tbl_name = table_match.group(1) if table_match else f"Statement {idx}"
                errors.append((tbl_name, str(e)))
                print(f"[{idx}/{len(statements)}] Error creating {tbl_name}: {e}")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    print("\n--- IMPORT SUMMARY ---")
    print(f"Successfully executed: {success_count}")
    print(f"Errors encountered   : {error_count}")
    if errors:
        print("Error details:")
        for tbl, err in errors:
            print(f"  - {tbl}: {err}")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nTotal tables now in database '{connection.settings_dict['NAME']}': {len(all_tables)}")

if __name__ == "__main__":
    run_import()
