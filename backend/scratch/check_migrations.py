import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY applied")
rows = cursor.fetchall()
print(f"Total applied migrations in django_migrations: {len(rows)}")
for r in rows:
    print(r)
