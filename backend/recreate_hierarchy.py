import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from accounting.models import MasterHierarchyRaw

print("Dropping broken table...")
with connection.cursor() as c:
    c.execute("DROP TABLE IF EXISTS master_hierarchy_raw;")
print("Dropped!")

print("Recreating table using Django schema editor...")
with connection.schema_editor() as schema_editor:
    schema_editor.create_model(MasterHierarchyRaw)
print("Created successfully!")
