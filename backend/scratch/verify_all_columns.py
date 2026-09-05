import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.apps import apps
from django.db import connection

def check_all_models():
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = set(row[0] for row in cursor.fetchall())

        missing = []
        for model in apps.get_models():
            db_table = model._meta.db_table
            if db_table not in all_tables:
                print(f"[MISSING TABLE] {model.__name__} -> {db_table}")
                continue

            cursor.execute(f"DESCRIBE `{db_table}`;")
            db_cols = set(row[0] for row in cursor.fetchall())

            for field in model._meta.fields:
                column = field.column
                if column and column not in db_cols:
                    missing.append((model.__name__, db_table, column, field.get_internal_type()))

        if missing:
            print("\n--- MISSING COLUMNS DETECTED ---")
            for m, t, c, dtype in missing:
                print(f"Model: {m}, Table: {t}, Column: {c} ({dtype})")
        else:
            print("\nAll Django model columns exist in database!")

if __name__ == "__main__":
    check_all_models()
