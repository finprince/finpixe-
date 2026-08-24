import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.apps import apps

def create_missing_tables():
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        cursor.execute("SHOW TABLES;")
        physical_tables = set(row[0] for row in cursor.fetchall())

    all_models = apps.get_models()
    created_count = 0
    errors = []

    for model in all_models:
        table = model._meta.db_table
        if table not in physical_tables:
            try:
                with connection.schema_editor() as schema_editor:
                    schema_editor.execute("SET FOREIGN_KEY_CHECKS=0;")
                    schema_editor.create_model(model)
                    schema_editor.execute("SET FOREIGN_KEY_CHECKS=1;")
                print(f"[CREATED] App: {model._meta.app_label} | Model: {model.__name__} | Table: {table}")
                created_count += 1
            except Exception as e:
                errors.append(f"[ERROR] App {model._meta.app_label}.{model.__name__} (Table '{table}'): {e}")

    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

    print(f"\nCreated {created_count} missing tables.")
    if errors:
        print(f"Encountered {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")

if __name__ == '__main__':
    create_missing_tables()
