import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vendors.po_mail_service import generate_po_html, generate_po_text, send_purchase_order_email
from vendors import vendorpo_database as db

sample_po = {
    'id': 999,
    'tenant_id': 'test-tenant',
    'po_number': 'PO-2026-TEST01',
    'po_date': '2026-09-03',
    'vendor_name': 'Jane & Co Supplies',
    'branch': 'Main Branch',
    'address_line1': '123 Market Street',
    'city': 'Bengaluru',
    'state': 'Karnataka',
    'pincode': '560001',
    'country': 'India',
    'email_address': 'ulaganathank38@gmail.com', # test recipient
    'contract_no': '9876541111',
    'receive_by': '2026-09-15',
    'receive_at': 'Main Warehouse - Bengaluru',
    'delivery_terms': 'Payment within 30 days of delivery. Goods subject to inspection.',
    'total_taxable_value': 10000.00,
    'total_tax': 2000.00,
    'total_value': 12000.00,
    'status': 'Approved',
    'items': [
        {
            'item_code': '01',
            'item_name': 'Stainless Steel Valves',
            'supplier_item_code': 'SS-V01',
            'quantity': 100,
            'uom': 'Nos',
            'negotiated_rate': 100.00,
            'final_rate': 100.00,
            'taxable_value': 10000.00,
            'gst_rate': 18.0,
            'gst_amount': 1800.00,
            'invoice_value': 11800.00
        },
        {
            'item_code': '02',
            'item_name': 'Industrial Gaskets',
            'supplier_item_code': 'GK-99',
            'quantity': 10,
            'uom': 'Pcs',
            'negotiated_rate': 20.00,
            'final_rate': 20.00,
            'taxable_value': 200.00,
            'gst_rate': 18.0,
            'gst_amount': 36.00,
            'invoice_value': 236.00
        }
    ]
}

sample_company = {
    'name': 'Finpixe AI Accounting Ltd',
    'branch_name': 'Headquarters - Bangalore',
    'gstin': '29ABCDE1234F1Z5',
    'address': 'Finpixe Tower, Tech Park',
    'city_state': 'Bengaluru, Karnataka - 560100',
    'phone': '+91 98765 43210',
    'email': 'accounts@finpixe.com'
}

html = generate_po_html(sample_po, sample_company)
print(f"Generated HTML length: {len(html)} chars")
text = generate_po_text(sample_po, sample_company)
print(f"Generated Text:\n{text}")

print("Test complete!")
