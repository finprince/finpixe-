import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from pending_purchases.models import PendingPurchase

print("Searching InvoiceTempOCR records for HSN 8210, 6116, 8205...")
found = []
for record in InvoiceTempOCR.objects.all().order_by('-created_at'):
    data = record.extracted_data or {}
    items = data.get('items') or []
    if not items and data.get('assembled_exports'):
        items = (data['assembled_exports'][0] or {}).get('items', [])
    if not items and data.get('sections'):
        items = (data['sections'] or {}).get('items', [])
        
    for item in items:
        hsn = str(item.get('hsn_code') or item.get('hsn') or '')
        if '8210' in hsn or '6116' in hsn or '8205' in hsn:
            found.append(record)
            break

print(f"Found {len(found)} matching records in InvoiceTempOCR:")
for r in found[:5]:
    print(f"  ID: {r.id}, Invoice: {r.supplier_invoice_no}, Status: {r.status}, Validation Status: {r.validation_status}")
    print(f"  File: {r.file_path}")

print("\nSearching PendingPurchase records...")
pp_found = []
for pp in PendingPurchase.objects.all().order_by('-updated_at'):
    payload = pp.extraction_payload or {}
    items = payload.get('items') or []
    if not items and payload.get('assembled_exports'):
        items = (payload['assembled_exports'][0] or {}).get('items', [])
    if not items and payload.get('sections'):
        items = (payload['sections'] or {}).get('items', [])
        
    for item in items:
        hsn = str(item.get('hsn_code') or item.get('hsn') or '')
        if '8210' in hsn or '6116' in hsn or '8205' in hsn:
            pp_found.append(pp)
            break

print(f"Found {len(pp_found)} matching records in PendingPurchase:")
for pp in pp_found[:5]:
    print(f"  ID: {pp.id}, Invoice: {pp.invoice_number}, Status: {pp.pending_purchase_status}, source_scan_row_id: {pp.source_scan_row_id}")
