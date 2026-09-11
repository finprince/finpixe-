import os
import sys
import csv
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounting.models import MasterHierarchyRaw

def import_hierarchy_csv(csv_path):
    print(f"Starting import of {csv_path} into master_hierarchy_raw using Django ORM...")
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found at {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        print("Deleting existing records...")
        MasterHierarchyRaw.objects.all().delete()
        
        instances = []
        for row in reader:
            # Map CSV headers to Django Model fields
            # The CSV headers are: Type of Business, Financial Reporting, Major Group, Group, Sub-group 1, Sub-group 2, Sub-group 3, Ledgers, Code
            
            def val(h1, h2):
                v = row.get(h1) or row.get(h2)
                return None if not v or v.strip() == '' or v.strip() == '-' else v.strip()

            instance = MasterHierarchyRaw(
                type_of_business_1=val('Type of Business', 'type_of_business_1'),
                financial_reporting_1=val('Financial Reporting', 'financial_reporting_1'),
                major_group_1=val('Major Group', 'major_group_1'),
                group_1=val('Group', 'group_1'),
                sub_group_1_1=val('Sub-group 1', 'sub_group_1_1'),
                sub_group_2_1=val('Sub-group 2', 'sub_group_2_1'),
                sub_group_3_1=val('Sub-group 3', 'sub_group_3_1'),
                ledger_1=val('Ledgers', 'ledger_1'),
                code=val('Code', 'code')
            )
            instances.append(instance)
            
        print(f"Bulk creating {len(instances)} rows...")
        MasterHierarchyRaw.objects.bulk_create(instances, batch_size=1000)
            
    print("Import completed successfully!")

if __name__ == "__main__":
    candidates = [
        os.path.join(backend_dir, "ledgers.csv"),
        os.path.join(backend_dir, "ledger_list_final_v7.csv"),
        "/app/ledgers.csv",
        "/app/ledger_list_final_v7.csv",
        r"C:\Users\subik\Downloads\ledgers.csv",
        r"C:\Users\subik\Downloads\ledger_list_final_v7.csv",
    ]
    csv_file_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    import_hierarchy_csv(csv_file_path)

