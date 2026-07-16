import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.normalize import get_normalized_items
from ocr_pipeline.pipeline import run_gst_validation_engine

# Load record
r = InvoiceTempOCR.objects.get(id=1009545)
ext = r.extracted_data or {}
raw_ai = ext.get('_raw_extraction') or {}
norm_items = get_normalized_items(raw_ai, tenant_id=r.tenant_id)

print("="*80)
print("STAGE-BY-STAGE FIELD EXTRACTION")
print("="*80)

# PDF Ground Truth
print("\n--- STAGE: PDF (Ground Truth) ---")
pdf_items = [
    {
        "hsn": "8210",
        "description": "Lab Coat Blue Colour",
        "taxable": 450.00,
        "qty": 1.0,
        "rate": 450.00,
        "gst_rate": 5.0,
        "cgst_rate": 2.5,
        "sgst_rate": 2.5,
        "igst_rate": 0.0,
        "cgst_amount": 11.25,
        "sgst_amount": 11.25,
        "igst_amount": 0.0,
        "expected_gst": 22.50,
        "current_gst": 22.50
    },
    {
        "hsn": "6116",
        "description": "Knitted Gloves",
        "taxable": 288.00,
        "qty": 12.0,
        "rate": 24.00,
        "gst_rate": 5.0,
        "cgst_rate": 2.5,
        "sgst_rate": 2.5,
        "igst_rate": 0.0,
        "cgst_amount": 7.20,
        "sgst_amount": 7.20,
        "igst_amount": 0.0,
        "expected_gst": 14.40,
        "current_gst": 14.40
    },
    {
        "hsn": "8205",
        "description": "Lathe Chuck Key 7/16\"",
        "taxable": 270.00,
        "qty": 1.0,
        "rate": 270.00,
        "gst_rate": 18.0,
        "cgst_rate": 9.0,
        "sgst_rate": 9.0,
        "igst_rate": 0.0,
        "cgst_amount": 24.30,
        "sgst_amount": 24.30,
        "igst_amount": 0.0,
        "expected_gst": 48.60,
        "current_gst": 48.60
    }
]
for idx, item in enumerate(pdf_items):
    print(f"Item {idx+1}: HSN={item['hsn']} | Desc={item['description']} | Taxable={item['taxable']} | Qty={item['qty']} | Rate={item['rate']} | GST Rate={item['gst_rate']}% | CGST Rate={item['cgst_rate']}% | SGST Rate={item['sgst_rate']}% | IGST Rate={item['igst_rate']}% | CGST={item['cgst_amount']} | SGST={item['sgst_amount']} | IGST={item['igst_amount']} | Expected GST={item['expected_gst']} | Current GST={item['current_gst']}")

# OCR Stage
print("\n--- STAGE: OCR Output ---")
ocr_items = [
    {
        "hsn": "8210",
        "description": "Lab Coat Blue Colour",
        "taxable": 450.00,
        "qty": 1.0,
        "rate": 450.00,
        "gst_rate": 5.0,
        "cgst_rate": "None",
        "sgst_rate": "None",
        "igst_rate": "None",
        "cgst_amount": "None",
        "sgst_amount": "None",
        "igst_amount": "None",
        "expected_gst": "None",
        "current_gst": "None"
    },
    {
        "hsn": "6116",
        "description": "Knitted Gloves",
        "taxable": 288.00,
        "qty": 12.0,
        "rate": 24.00,
        "gst_rate": 5.0,
        "cgst_rate": "None",
        "sgst_rate": "None",
        "igst_rate": "None",
        "cgst_amount": "None",
        "sgst_amount": "None",
        "igst_amount": "None",
        "expected_gst": "None",
        "current_gst": "None"
    },
    {
        "hsn": "8205",
        "description": "Lathe Chuck Key 7/16\"",
        "taxable": 270.00,
        "qty": 1.0,
        "rate": 270.00,
        "gst_rate": 18.0,
        "cgst_rate": "None",
        "sgst_rate": "None",
        "igst_rate": "None",
        "cgst_amount": "None",
        "sgst_amount": "None",
        "igst_amount": "None",
        "expected_gst": "None",
        "current_gst": "None"
    }
]
for idx, item in enumerate(ocr_items):
    print(f"Item {idx+1}: HSN={item['hsn']} | Desc={item['description']} | Taxable={item['taxable']} | Qty={item['qty']} | Rate={item['rate']} | GST Rate={item['gst_rate']}% | CGST Rate={item['cgst_rate']} | SGST Rate={item['sgst_rate']} | IGST Rate={item['igst_rate']} | CGST={item['cgst_amount']} | SGST={item['sgst_amount']} | IGST={item['igst_amount']} | Expected GST={item['expected_gst']} | Current GST={item['current_gst']}")

# Raw AI JSON Stage
print("\n--- STAGE: Raw AI Extraction JSON ---")
for idx, item in enumerate(raw_ai.get('items', [])):
    hsn = item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('quantity')
    rate = item.get('rate')
    gst_rate = item.get('gst_rate') # usually None
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst_amount')
    sgst_amount = item.get('sgst_amount')
    igst_amount = item.get('igst_amount')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate} | CGST Rate={cgst_rate} | SGST Rate={sgst_rate} | IGST Rate={igst_rate} | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Normalizer Input
print("\n--- STAGE: Normalizer Input ---")
for idx, item in enumerate(raw_ai.get('items', [])):
    hsn = item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('quantity')
    rate = item.get('rate')
    gst_rate = item.get('gst_rate') # usually None
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst_amount')
    sgst_amount = item.get('sgst_amount')
    igst_amount = item.get('igst_amount')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate} | CGST Rate={cgst_rate} | SGST Rate={sgst_rate} | IGST Rate={igst_rate} | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Normalizer Output
print("\n--- STAGE: Normalizer Output ---")
for idx, item in enumerate(norm_items):
    hsn = item.get('hsn_sac')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty')
    rate = item.get('rate')
    gst_rate = item.get('computed_gst_rate')
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst')
    sgst_amount = item.get('sgst')
    igst_amount = item.get('igst')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Database (InvoiceTempOCR JSON)
print("\n--- STAGE: Database (InvoiceTempOCR JSON) ---")
db_items = ext.get('items', [])
for idx, item in enumerate(db_items):
    hsn = item.get('hsn_sac') or item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty') or item.get('quantity')
    rate = item.get('rate')
    gst_rate = item.get('computed_gst_rate') or item.get('gst_rate')
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst') or item.get('cgst_amount')
    sgst_amount = item.get('sgst') or item.get('sgst_amount')
    igst_amount = item.get('igst') or item.get('igst_amount')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Validation Engine
print("\n--- STAGE: GST Validation Engine ---")
# Validation engine computes expected_gst for each item
is_interstate = True # treated as interstate because company_gstin was empty
for idx, item in enumerate(db_items):
    hsn = item.get('hsn_sac') or item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty') or item.get('quantity')
    rate = item.get('rate')
    cgst_rate = float(item.get('cgst_rate') or 0.0)
    sgst_rate = float(item.get('sgst_rate') or 0.0)
    igst_rate = float(item.get('igst_rate') or 0.0)
    gst_rate = cgst_rate + sgst_rate + igst_rate
    
    expected_igst_item = round(taxable * gst_rate / 100.0, 2)
    expected_cgst_item = 0.0
    expected_sgst_item = 0.0
    expected_gst = expected_cgst_item + expected_sgst_item + expected_igst_item
    
    current_cgst = float(item.get('cgst') or item.get('cgst_amount') or 0.0)
    current_sgst = float(item.get('sgst') or item.get('sgst_amount') or 0.0)
    current_igst = float(item.get('igst') or item.get('igst_amount') or 0.0)
    current_gst = current_cgst + current_sgst + current_igst
    
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST={expected_cgst_item} | SGST={expected_sgst_item} | IGST={expected_igst_item} | Expected GST={expected_gst} | Current GST={current_gst}")

# API Response
print("\n--- STAGE: API Response ---")
# API returns staging_row's extracted_data
for idx, item in enumerate(db_items):
    hsn = item.get('hsn_sac') or item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty') or item.get('quantity')
    rate = item.get('rate')
    gst_rate = item.get('computed_gst_rate') or item.get('gst_rate')
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst') or item.get('cgst_amount')
    sgst_amount = item.get('sgst') or item.get('sgst_amount')
    igst_amount = item.get('igst') or item.get('igst_amount')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Frontend State
print("\n--- STAGE: Frontend State ---")
for idx, item in enumerate(db_items):
    hsn = item.get('hsn_sac') or item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty') or item.get('quantity')
    rate = item.get('rate')
    gst_rate = item.get('computed_gst_rate') or item.get('gst_rate')
    cgst_rate = item.get('cgst_rate')
    sgst_rate = item.get('sgst_rate')
    igst_rate = item.get('igst_rate')
    cgst_amount = item.get('cgst') or item.get('cgst_amount')
    sgst_amount = item.get('sgst') or item.get('sgst_amount')
    igst_amount = item.get('igst') or item.get('igst_amount')
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST={cgst_amount} | SGST={sgst_amount} | IGST={igst_amount} | Expected GST=None | Current GST=None")

# Rendered UI (Dialog)
print("\n--- STAGE: Rendered UI ---")
# UI computes expected_gst for display
for idx, item in enumerate(db_items):
    hsn = item.get('hsn_sac') or item.get('hsn_code')
    desc = item.get('description')
    taxable = item.get('taxable_value')
    qty = item.get('qty') or item.get('quantity')
    rate = item.get('rate')
    cgst_rate = float(item.get('cgst_rate') or 0.0)
    sgst_rate = float(item.get('sgst_rate') or 0.0)
    igst_rate = float(item.get('igst_rate') or 0.0)
    gst_rate = cgst_rate + sgst_rate + igst_rate
    expected_gst = round(taxable * gst_rate / 100.0, 2)
    
    current_cgst = float(item.get('cgst') or item.get('cgst_amount') or 0.0)
    current_sgst = float(item.get('sgst') or item.get('sgst_amount') or 0.0)
    current_igst = float(item.get('igst') or item.get('igst_amount') or 0.0)
    current_gst = current_cgst + current_sgst + current_igst
    print(f"Item {idx+1}: HSN={hsn} | Desc={desc} | Taxable={taxable} | Qty={qty} | Rate={rate} | GST Rate={gst_rate}% | CGST Rate={cgst_rate}% | SGST Rate={sgst_rate}% | IGST Rate={igst_rate}% | CGST=None | SGST=None | IGST=None | Expected GST={expected_gst} | Current GST={current_gst}")
