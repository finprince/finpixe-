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

print("=======================================================")
print(" RIM SYSTEM 1-2-3 COMPLETE INVENTORY DOMAIN SEEDER")
print("=======================================================\n")

inventory_payloads = [
    {
        "item_code": "SKU-SER-001", "item_name": "Dell PowerEdge Server 16G",
        "category": "IT Hardware", "uom": "PCS", "opening_qty": 15.0, "rate": 120000.0, "valuation": 1800000.0,
        "hsn": "8471", "gst": 18.0, "reorder": 5.0
    },
    {
        "item_code": "SKU-LIC-002", "item_name": "FINPIXE Enterprise Cloud License",
        "category": "Software Subscriptions", "uom": "NOS", "opening_qty": 50.0, "rate": 25000.0, "valuation": 1250000.0,
        "hsn": "9973", "gst": 18.0, "reorder": 10.0
    },
    {
        "item_code": "SKU-NET-003", "item_name": "Cisco Catalyst 9300 48-Port Switch",
        "category": "Networking Equipment", "uom": "PCS", "opening_qty": 20.0, "rate": 45000.0, "valuation": 900000.0,
        "hsn": "8517", "gst": 18.0, "reorder": 4.0
    },
    {
        "item_code": "SKU-SEC-004", "item_name": "Fortinet FortiGate 100F Firewall",
        "category": "Cybersecurity Systems", "uom": "PCS", "opening_qty": 8.0, "rate": 85000.0, "valuation": 680000.0,
        "hsn": "8517", "gst": 18.0, "reorder": 2.0
    },
    {
        "item_code": "SKU-UPS-005", "item_name": "APC Smart-UPS RT 10kVA",
        "category": "Power Backup", "uom": "SETS", "opening_qty": 12.0, "rate": 65000.0, "valuation": 780000.0,
        "hsn": "8504", "gst": 18.0, "reorder": 3.0
    }
]

categories = [
    ("IT Hardware", "HWARE"),
    ("Software Subscriptions", "SOFTW"),
    ("Networking Equipment", "NETWK"),
    ("Cybersecurity Systems", "SECUT"),
    ("Power Backup", "POWER")
]

locations = [
    ("LOC-MUM-01", "Main Plant Warehouse", "Mumbai, Maharashtra"),
    ("LOC-BLR-02", "Tech Park Store", "Bengaluru, Karnataka"),
    ("LOC-MAA-03", "Logistics Hub", "Chennai, Tamil Nadu")
]

tenants = ['6d114c1e-647d-4884-b385-f3d806547476', 'default', 'anonymous']

with connection.cursor() as cursor:
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    for tid in tenants:
        # A. Categories
        for cat_name, cat_code in categories:
            cursor.execute("""
                INSERT INTO inventory_master_category
                (tenant_id, category_name, category_code, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 1, NOW(), NOW())
                ON DUPLICATE KEY UPDATE category_name = VALUES(category_name);
            """, [tid, cat_name, cat_code])

        # B. Locations / Warehouses
        for loc_code, loc_name, addr in locations:
            cursor.execute("""
                INSERT INTO inventory_location
                (tenant_id, location_code, location_name, address, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 1, NOW(), NOW())
                ON DUPLICATE KEY UPDATE location_name = VALUES(location_name);
            """, [tid, loc_code, loc_name, addr])

        # C. Master Inventory Items
        for item in inventory_payloads:
            cursor.execute("""
                INSERT INTO inventory_master_inventoryitems
                (tenant_id, item_code, item_name, uom, rate, rate_unit, hsn_code, gst_rate, reorder_level, is_saleable, is_active, opening_stock, opening_rate, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'INR', %s, %s, %s, 1, 1, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE item_name = VALUES(item_name), opening_stock = VALUES(opening_stock), rate = VALUES(rate), tenant_id = VALUES(tenant_id);
            """, [tid, item['item_code'], item['item_name'], item['uom'], item['rate'], item['hsn'], item['gst'], item['reorder'], item['opening_qty'], item['rate']])

    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

print("INVENTORY SEEDING COMPLETED FOR ALL TENANTS SUCCESSFUL!")
