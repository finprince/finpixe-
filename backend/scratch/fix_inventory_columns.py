import os
import sys

# Add parent and current dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

def check_and_add_columns():
    with connection.cursor() as cursor:
        cursor.execute("DESCRIBE inventory_master_inventoryitems;")
        existing_cols = {row[0]: row[1] for row in cursor.fetchall()}
        print("Existing columns in inventory_master_inventoryitems:")
        for col, dtype in existing_cols.items():
            print(f"  - {col}: {dtype}")

        queries = []
        if 'opening_stock' not in existing_cols:
            queries.append("ALTER TABLE inventory_master_inventoryitems ADD COLUMN opening_stock decimal(15,3) NOT NULL DEFAULT 0.000 AFTER is_saleable;")
        if 'opening_rate' not in existing_cols:
            queries.append("ALTER TABLE inventory_master_inventoryitems ADD COLUMN opening_rate decimal(15,2) NOT NULL DEFAULT 0.00 AFTER opening_stock;")

        for q in queries:
            print(f"Executing: {q}")
            cursor.execute(q)

        cursor.execute("DESCRIBE inventory_master_inventoryitems;")
        updated_cols = {row[0]: row[1] for row in cursor.fetchall()}
        print("\nUpdated columns in inventory_master_inventoryitems:")
        for col, dtype in updated_cols.items():
            print(f"  - {col}: {dtype}")

if __name__ == "__main__":
    check_and_add_columns()
