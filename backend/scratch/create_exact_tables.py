import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.apps import apps
from django.db import connection

models_to_create = [
    apps.get_model('core', 'RAGReindexJob'),
    apps.get_model('core', 'RAGActiveIndex'),
    apps.get_model('gst_reconciliation', 'GSTElectronicLedger'),
    apps.get_model('gst_reconciliation', 'GSTLateFee'),
]

with connection.cursor() as cursor:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for m in models_to_create:
        cursor.execute(f"DROP TABLE IF EXISTS `{m._meta.db_table}`;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

with connection.schema_editor() as schema_editor:
    for m in models_to_create:
        print(f"Creating exact schema for {m.__name__} ({m._meta.db_table})")
        schema_editor.create_model(m)

print("Done creating models with schema_editor!")
