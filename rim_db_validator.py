import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.apps import apps

class System1_DatabaseExtractor:
    """System 1 (Perception): Inspects physical DB schema and Django models."""

    def get_physical_tables(self):
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = [row[0] for row in cursor.fetchall()]
        return set(tables)

    def get_table_columns(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`;")
            columns = [row[0] for row in cursor.fetchall()]
        return set(columns)

    def get_django_models_meta(self):
        models_meta = []
        all_models = apps.get_models()
        for model in all_models:
            db_table = model._meta.db_table
            fields = [field.column for field in model._meta.concrete_fields if field.column]
            models_meta.append({
                "app": model._meta.app_label,
                "model_name": model.__name__,
                "db_table": db_table,
                "fields": set(fields)
            })
        return models_meta


class System2_DatabaseRulesVerifier:
    """System 2 (Deterministic Rules Engine): Validates schema alignment."""

    def __init__(self, physical_tables, models_meta, extractor):
        self.physical_tables = physical_tables
        self.models_meta = models_meta
        self.extractor = extractor

    def verify_table_existence(self):
        missing_tables = []
        existing_tables = []
        for meta in self.models_meta:
            table = meta["db_table"]
            if table in self.physical_tables:
                existing_tables.append(meta)
            else:
                missing_tables.append(meta)
        return existing_tables, missing_tables

    def verify_column_alignment(self, existing_tables):
        mismatched_columns = []
        aligned_tables = 0
        for meta in existing_tables:
            table = meta["db_table"]
            expected_fields = meta["fields"]
            try:
                actual_columns = self.extractor.get_table_columns(table)
                missing_fields = expected_fields - actual_columns
                if missing_fields:
                    mismatched_columns.append({
                        "model": f"{meta['app']}.{meta['model_name']}",
                        "table": table,
                        "missing_columns": list(missing_fields)
                    })
                else:
                    aligned_tables += 1
            except Exception as e:
                mismatched_columns.append({
                    "model": f"{meta['app']}.{meta['model_name']}",
                    "table": table,
                    "error": str(e)
                })
        return aligned_tables, mismatched_columns

    def verify_table_rows(self, existing_tables):
        counts = {}
        with connection.cursor() as cursor:
            for meta in existing_tables[:15]:  # Sample top tables
                table = meta["db_table"]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
                    counts[table] = cursor.fetchone()[0]
                except Exception:
                    pass
        return counts


class System3_MetaCognitiveDatabaseAuditor:
    """System 3 (Meta-Cognition): Evaluates overall Database Schema Health."""

    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2

    def run_database_audit(self):
        print("\n=======================================================")
        print(" RIM SYSTEM 1-2-3 DATABASE SCHEMA & INTEGRITY AUDIT")
        print("=======================================================\n")

        # System 1: Schema Perception
        print("[SYSTEM 1 - SCHEMA EXTRACTION]")
        physical_tables = self.s1.get_physical_tables()
        models_meta = self.s1.get_django_models_meta()
        print(f"  -> Physical Database Name: '{connection.settings_dict['NAME']}'")
        print(f"  -> Total Physical MySQL Tables Found: {len(physical_tables)}")
        print(f"  -> Total Django Model Definitions: {len(models_meta)}")

        # System 2: Logic & Rule Checks
        print("\n[SYSTEM 2 - DETERMINISTIC SCHEMA RULE VERIFICATION]")
        
        existing_tables, missing_tables = self.s2.verify_table_existence()
        if missing_tables:
            print(f"  [FAIL] Missing Tables ({len(missing_tables)}):")
            for m in missing_tables:
                print(f"   - {m['app']}.{m['model_name']} -> expected db_table '{m['db_table']}'")
        else:
            print(f"  [PASS] Table Existence: All {len(models_meta)} Django models have corresponding physical MySQL tables.")

        aligned_tables, column_mismatches = self.s2.verify_column_alignment(existing_tables)
        if column_mismatches:
            print(f"  [WARN] Column Mismatches ({len(column_mismatches)}):")
            for cm in column_mismatches:
                print(f"   - {cm['model']} (table '{cm['table']}'): missing columns -> {cm.get('missing_columns', cm.get('error'))}")
        else:
            print(f"  [PASS] Column Alignment: 100% of fields match physical DB columns across all {aligned_tables} tables.")

        sample_counts = self.s2.verify_table_rows(existing_tables)
        print("\n[CHECK: Physical Table Row Telemetry]")
        for tbl, count in list(sample_counts.items())[:10]:
            print(f"   - Table `{tbl}`: {count} row(s)")

        # System 3: Health Index & Synthesis
        print("\n=======================================================")
        total_models = len(models_meta)
        passed_tables = len(existing_tables)
        passed_columns = aligned_tables
        
        health_score = int(((passed_tables + passed_columns) / (2 * total_models)) * 100) if total_models > 0 else 0

        print(f" DATABASE HEALTH INDEX: {health_score}/100")
        print("=======================================================")
        print("Summary:")
        print(f" -> Total Physical Tables: {len(physical_tables)}")
        print(f" -> Model Table Matching: {passed_tables}/{total_models}")
        print(f" -> Column Alignment: {passed_columns}/{total_models}")
        print("=======================================================\n")

if __name__ == '__main__':
    s1 = System1_DatabaseExtractor()
    physical_tables = s1.get_physical_tables()
    models_meta = s1.get_django_models_meta()
    s2 = System2_DatabaseRulesVerifier(physical_tables, models_meta, s1)
    s3 = System3_MetaCognitiveDatabaseAuditor(s1, s2)
    s3.run_database_audit()
