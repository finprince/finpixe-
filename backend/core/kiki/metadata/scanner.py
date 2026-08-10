"""
MySQL Metadata Schema Scanner
=============================
Inspects MySQL information_schema to discover tables, columns, data types, PKs, and foreign keys.
"""
from django.db import connection
from typing import Dict, Any, List

class MySQLSchemaScanner:
    """Introspects MySQL database topology dynamically."""

    def scan_schema(self) -> Dict[str, Any]:
        """Scan all active tables and metadata in the current database."""
        catalog = {
            "tables": {},
            "foreign_keys": []
        }
        
        with connection.cursor() as cursor:
            # 1. Fetch all tables
            cursor.execute("""
                SELECT table_name, table_rows 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
            """)
            tables = cursor.fetchall()
            
            for table_name, table_rows in tables:
                catalog["tables"][table_name] = {
                    "columns": {},
                    "primary_key": None,
                    "estimated_rows": table_rows or 0
                }

            # 2. Fetch all columns
            cursor.execute("""
                SELECT table_name, column_name, data_type, column_key, is_nullable
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                ORDER BY table_name, ordinal_position
            """)
            columns = cursor.fetchall()
            for table_name, col_name, data_type, col_key, is_nullable in columns:
                if table_name in catalog["tables"]:
                    catalog["tables"][table_name]["columns"][col_name] = {
                        "type": data_type,
                        "is_nullable": is_nullable == 'YES',
                        "is_key": col_key != ''
                    }
                    if col_key == 'PRI':
                        catalog["tables"][table_name]["primary_key"] = col_name

            # 3. Fetch foreign key relationships
            cursor.execute("""
                SELECT 
                    table_name, column_name, 
                    referenced_table_name, referenced_column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = DATABASE() 
                  AND referenced_table_name IS NOT NULL
            """)
            fks = cursor.fetchall()
            for t_name, c_name, ref_t_name, ref_c_name in fks:
                catalog["foreign_keys"].append({
                    "from_table": t_name,
                    "from_column": c_name,
                    "to_table": ref_t_name,
                    "to_column": ref_c_name
                })

        return catalog
