import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from vendors.po_mail_service import generate_po_html, generate_po_text

sample_po = {
    'id': 1,
    'tenant_id': 'test',
    'po_number': 'PO-2026-TEST01',
    'po_date': '2026-09-03',
    'vendor_name': 'Jane & Co Supplies',
    'branch': 'Main Branch',
    'address_line1': '123 Market Street',
    'city': 'Bengaluru',
    'state': 'Karnataka',
    'pincode': '560001',
    'country': 'India',
    'email_address': 'ulaganathank38@gmail.com',
    'contract_no': '9876541111',
    'receive_by': '2026-09-15',
    'receive_at': 'Main Warehouse - Bengaluru',
    'delivery_terms': 'Payment within 30 days of delivery.',
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
        }
    ]
}

sample_company = {
    'name': 'Finpixe AI Accounting',
    'branch_name': 'Headquarters - Bangalore',
    'gstin': '29ABCDE1234F1Z5',
    'address': 'Tech Park',
    'city_state': 'Bengaluru, Karnataka',
    'phone': '+91 98765 43210',
    'email': 'accounts@finpixe.com'
}

subject = f"Purchase Order {sample_po['po_number']} - {sample_company['name']}"
text_body = generate_po_text(sample_po, sample_company)
html_body = generate_po_html(sample_po, sample_company)

from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'ulaganathank38@gmail.com')
to_email = 'ulaganathank38@gmail.com'

msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
msg.attach_alternative(html_body, "text/html")
res = msg.send(fail_silently=False)
print(f"Email sent result: {res}")
