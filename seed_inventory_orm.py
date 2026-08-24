import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from inventory.models import InventoryItem, InventoryMasterCategory, InventoryLocation

items_data = [
    {
        "item_code": "SKU-SER-001", "item_name": "Dell PowerEdge Server 16G",
        "description": "High performance 2U dual socket rack server",
        "uom": "PCS", "opening_stock": 15.0, "rate": 120000.0, "opening_rate": 120000.0,
        "hsn_code": "8471", "gst_rate": 18.0, "reorder_level": 5.0
    },
    {
        "item_code": "SKU-LIC-002", "item_name": "FINPIXE Enterprise Cloud License",
        "description": "Annual cloud SaaS license for enterprise AI accounting",
        "uom": "NOS", "opening_stock": 50.0, "rate": 25000.0, "opening_rate": 25000.0,
        "hsn_code": "9973", "gst_rate": 18.0, "reorder_level": 10.0
    },
    {
        "item_code": "SKU-NET-003", "item_name": "Cisco Catalyst 9300 48-Port Switch",
        "description": "Enterprise layer 3 gigabit ethernet switch",
        "uom": "PCS", "opening_stock": 20.0, "rate": 45000.0, "opening_rate": 45000.0,
        "hsn_code": "8517", "gst_rate": 18.0, "reorder_level": 4.0
    },
    {
        "item_code": "SKU-SEC-004", "item_name": "Fortinet FortiGate 100F Firewall",
        "description": "Next generation network firewall appliance",
        "uom": "PCS", "opening_stock": 8.0, "rate": 85000.0, "opening_rate": 85000.0,
        "hsn_code": "8517", "gst_rate": 18.0, "reorder_level": 2.0
    },
    {
        "item_code": "SKU-UPS-005", "item_name": "APC Smart-UPS RT 10kVA",
        "description": "On-line double conversion power backup system",
        "uom": "SETS", "opening_stock": 12.0, "rate": 65000.0, "opening_rate": 65000.0,
        "hsn_code": "8504", "gst_rate": 18.0, "reorder_level": 3.0
    }
]

tenants = ['6d114c1e-647d-4884-b385-f3d806547476', 'default', 'anonymous']

created_count = 0
for tid in tenants:
    for data in items_data:
        item, created = InventoryItem.objects.update_or_create(
            tenant_id=tid,
            item_code=data["item_code"],
            defaults={
                "item_name": data["item_name"],
                "description": data["description"],
                "uom": data["uom"],
                "rate": data["rate"],
                "opening_stock": data["opening_stock"],
                "opening_rate": data["opening_rate"],
                "hsn_code": data["hsn_code"],
                "gst_rate": data["gst_rate"],
                "reorder_level": data["reorder_level"],
                "is_saleable": True,
                "is_active": True,
            }
        )
        created_count += 1
        print(f"[{tid}] Seeded Item: {item.item_code} | {item.item_name} | Qty: {item.opening_stock}")

print(f"\n=======================================================")
print(f" SEEDED {created_count} INVENTORY ITEMS VIA DJANGO ORM")
print(f"=======================================================\n")
