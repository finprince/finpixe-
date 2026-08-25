import os
import sys
import hashlib
from datetime import date
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from gst_reconciliation.models import GSTR2BInvoice, ReconciliationResult
from accounting.models_voucher_purchase import (
    VoucherPurchaseSupplierDetails,
    VoucherPurchaseItem,
    VoucherPurchaseDueDetails
)
from vendors.models import VendorMasterBasicDetail
from accounting.models import MasterLedger

def seed_reconciliation():
    print("Starting seed data generation for GSTR-2B Reconciliation...")

    # Clear previous reconciliation test results
    ReconciliationResult.objects.all().delete()
    GSTR2BInvoice.objects.all().delete()
    VoucherPurchaseSupplierDetails.objects.filter(supplier_invoice_no__startswith='RECO-').delete()

    ledger = MasterLedger.objects.first()
    if not ledger:
        ledger = MasterLedger.objects.create(name='Purchase Account', group='Direct Expenses')

    tenant_id = 'default-tenant'

    vendor_a, _ = VendorMasterBasicDetail.objects.get_or_create(
        vendor_name='AccuTurn Industrial Supplies Ltd',
        defaults={
            'tenant_id': tenant_id,
            'email': 'supplies@accuturn.in',
            'contact_no': '9876543210',
            'ledger': ledger
        }
    )

    vendor_b, _ = VendorMasterBasicDetail.objects.get_or_create(
        vendor_name='Precision Tooling & Components Pvt Ltd',
        defaults={
            'tenant_id': tenant_id,
            'email': 'sales@precisiontooling.com',
            'contact_no': '9845012345',
            'ledger': ledger
        }
    )

    vendor_c, _ = VendorMasterBasicDetail.objects.get_or_create(
        vendor_name='Apex Logistics & Raw Materials',
        defaults={
            'tenant_id': tenant_id,
            'email': 'apex@materials.co',
            'contact_no': '9712345678',
            'ledger': ledger
        }
    )

    # -------------------------------------------------------------
    # 1. EXACT MATCHES (10 Records)
    # -------------------------------------------------------------
    print("Seeding 10 EXACT Match records...")
    exact_samples = [
        ("33AABCU9603R1ZM", "RECO-EXACT-001", "2025-01-05", Decimal("11800.00"), Decimal("10000.00"), Decimal("0.00"), Decimal("900.00"), Decimal("900.00"), "AccuTurn Industrial Supplies Ltd"),
        ("33AACD1234E1ZX", "RECO-EXACT-002", "2025-01-08", Decimal("23600.00"), Decimal("20000.00"), Decimal("3600.00"), Decimal("0.00"), Decimal("0.00"), "Precision Tooling & Components Pvt Ltd"),
        ("33AAABM5678K1ZP", "RECO-EXACT-003", "2025-01-10", Decimal("5900.00"), Decimal("5000.00"), Decimal("0.00"), Decimal("450.00"), Decimal("450.00"), "Apex Logistics & Raw Materials"),
        ("33AAACR9876L1ZT", "RECO-EXACT-004", "2025-01-12", Decimal("17700.00"), Decimal("15000.00"), Decimal("2700.00"), Decimal("0.00"), Decimal("0.00"), "AccuTurn Industrial Supplies Ltd"),
        ("27AABCT1234Q1ZA", "RECO-EXACT-005", "2025-01-15", Decimal("35400.00"), Decimal("30000.00"), Decimal("5400.00"), Decimal("0.00"), Decimal("0.00"), "Precision Tooling & Components Pvt Ltd"),
        ("33AAGCB1286Q1ZB", "RECO-EXACT-006", "2025-01-18", Decimal("47200.00"), Decimal("40000.00"), Decimal("0.00"), Decimal("3600.00"), Decimal("3600.00"), "Apex Logistics & Raw Materials"),
        ("33AALCS5544P1ZU", "RECO-EXACT-007", "2025-01-20", Decimal("8260.00"), Decimal("7000.00"), Decimal("1260.00"), Decimal("0.00"), Decimal("0.00"), "AccuTurn Industrial Supplies Ltd"),
        ("33AATCR7788M1ZR", "RECO-EXACT-008", "2025-01-22", Decimal("14160.00"), Decimal("12000.00"), Decimal("0.00"), Decimal("1080.00"), Decimal("1080.00"), "Precision Tooling & Components Pvt Ltd"),
        ("27AAACB9988C1Z9", "RECO-EXACT-009", "2025-01-25", Decimal("29500.00"), Decimal("25000.00"), Decimal("4500.00"), Decimal("0.00"), Decimal("0.00"), "Apex Logistics & Raw Materials"),
        ("33AAFFB3322E1Z2", "RECO-EXACT-010", "2025-01-28", Decimal("59000.00"), Decimal("50000.00"), Decimal("0.00"), Decimal("4500.00"), Decimal("4500.00"), "AccuTurn Industrial Supplies Ltd"),
    ]

    for gstin, inv_no, inv_date_str, val, txval, igst, cgst, sgst, v_name in exact_samples:
        d = date.fromisoformat(inv_date_str)
        fp = hashlib.sha256(f"{gstin}|{inv_no}|{inv_date_str}|{val}".encode()).hexdigest()
        inv_2b = GSTR2BInvoice.objects.create(
            gstin=gstin,
            vendor_name=v_name,
            invoice_no=inv_no,
            invoice_date=d,
            invoice_value=val,
            taxable_value=txval,
            igst=igst,
            cgst=cgst,
            sgst=sgst,
            cess=Decimal('0.00'),
            fingerprint=fp,
            raw_data={'fp': '012025', 'period': 'January 2024-25', 'rchrg': 'N', 'itcavl': 'Y'}
        )

        pv = VoucherPurchaseSupplierDetails.objects.create(
            date=d,
            supplier_invoice_no=inv_no,
            supplier_invoice_date=d,
            purchase_voucher_no=f"PV-{inv_no}",
            vendor_name=v_name,
            vendor_basic_detail=vendor_a,
            gstin=gstin,
            input_type='Interstate' if igst > 0 else 'Intrastate',
            tenant_id=tenant_id
        )
        VoucherPurchaseItem.objects.create(
            supplier_details=pv,
            item_code='ITEM-IND',
            item_name='Industrial Machinery Spares',
            quantity=Decimal('1.00'),
            rate=txval,
            taxable_value=txval,
            igst_amount=igst,
            cgst_amount=cgst,
            sgst_amount=sgst,
            cess_amount=Decimal('0.00'),
            invoice_value=val
        )
        VoucherPurchaseDueDetails.objects.create(
            supplier_details=pv,
            to_pay=val
        )

        ReconciliationResult.objects.create(
            invoice_2b=inv_2b,
            purchase_voucher_id=pv.id,
            matching_score=100,
            status='EXACT',
            matching_details={
                'status': 'EXACT',
                'matching_score': 100,
                'mismatches': [],
                'itc_availment': 'YES',
                'itc_availability': 'YES',
                'fields': [
                    {"field": "Supplier GSTIN", "status": "MATCH", "gstr2b": gstin, "books": gstin},
                    {"field": "Invoice Number", "status": "MATCH", "gstr2b": inv_no, "books": inv_no},
                    {"field": "Invoice Date", "status": "MATCH", "gstr2b": inv_date_str, "books": inv_date_str},
                    {"field": "Invoice Value", "status": "MATCH", "gstr2b": float(val), "books": float(val)},
                    {"field": "Taxable Value", "status": "MATCH", "gstr2b": float(txval), "books": float(txval)},
                    {"field": "IGST", "status": "MATCH", "gstr2b": float(igst), "books": float(igst)},
                    {"field": "CGST", "status": "MATCH", "gstr2b": float(cgst), "books": float(cgst)},
                    {"field": "SGST", "status": "MATCH", "gstr2b": float(sgst), "books": float(sgst)},
                    {"field": "Reverse Charge", "status": "MATCH", "gstr2b": "N", "books": "N"},
                    {"field": "ITC Availability", "status": "MATCH", "gstr2b": "YES", "books": "YES"},
                ],
                'books_data': {
                    'purchase_voucher_id': pv.id,
                    'invoice_no': inv_no,
                    'invoice_date': inv_date_str,
                    'invoice_value': float(val),
                    'taxable_value': float(txval),
                    'igst': float(igst),
                    'cgst': float(cgst),
                    'sgst': float(sgst),
                    'vendor_name': v_name,
                    'supplier_gstin': gstin,
                    'gstr_period': 'January 2024-25',
                    'reverse_charge': 'N',
                    'itc_availability': 'YES',
                }
            }
        )

    # -------------------------------------------------------------
    # 2. PARTIAL / MISMATCH (10 Records)
    # -------------------------------------------------------------
    print("Seeding 10 PARTIAL / MISMATCH records...")
    partial_samples = [
        ("33AABCU9603R1ZM", "RECO-PART-001", "2025-01-04", Decimal("15500.00"), Decimal("13000.00"), Decimal("0.00"), Decimal("1250.00"), Decimal("1250.00"), Decimal("15000.00"), Decimal("12711.86"), Decimal("0.00"), Decimal("1144.07"), Decimal("1144.07"), "012025", "N", "Y", "N", ["INVOICE VALUE MISMATCH"]),
        ("33AACD1234E1ZX", "RECO-PART-002", "2025-01-07", Decimal("28000.00"), Decimal("23728.81"), Decimal("4271.19"), Decimal("0.00"), Decimal("0.00"), Decimal("28000.00"), Decimal("23728.81"), Decimal("4271.19"), Decimal("0.00"), Decimal("0.00"), "012025", "N", "Y", "N", ["INVOICE DATE MISMATCH"]),
        ("33AAABM5678K1ZP", "RECO-PART-003", "2025-01-09", Decimal("9500.00"), Decimal("8050.85"), Decimal("0.00"), Decimal("724.57"), Decimal("724.57"), Decimal("9500.00"), Decimal("8050.85"), Decimal("0.00"), Decimal("724.57"), Decimal("724.57"), "012025", "N", "N", "N", ["ITC AVAILMENT BLOCKED"]),
        ("33AAACR9876L1ZT", "RECO-PART-004", "2025-01-11", Decimal("42000.00"), Decimal("35593.22"), Decimal("6406.78"), Decimal("0.00"), Decimal("0.00"), Decimal("41500.00"), Decimal("35169.49"), Decimal("6330.51"), Decimal("0.00"), Decimal("0.00"), "012025", "N", "Y", "N", ["TAXABLE VALUE MISMATCH", "INVOICE VALUE MISMATCH"]),
        ("27AABCT1234Q1ZA", "RECO-PART-005", "2025-01-14", Decimal("62500.00"), Decimal("52966.10"), Decimal("9533.90"), Decimal("0.00"), Decimal("0.00"), Decimal("62500.00"), Decimal("52966.10"), Decimal("9533.90"), Decimal("0.00"), Decimal("0.00"), "012025", "N", "Y", "Y", ["REVERSE CHARGE MISMATCH"]),
        ("33AAGCB1286Q1ZB", "RECO-PART-006", "2025-01-16", Decimal("18900.00"), Decimal("16016.95"), Decimal("0.00"), Decimal("1441.52"), Decimal("1441.52"), Decimal("18500.00"), Decimal("15677.97"), Decimal("0.00"), Decimal("1411.02"), Decimal("1411.02"), "012025", "N", "Y", "N", ["CGST MISMATCH", "SGST MISMATCH"]),
        ("33AALCS5544P1ZU", "RECO-PART-007", "2025-01-19", Decimal("31200.00"), Decimal("26440.68"), Decimal("4759.32"), Decimal("0.00"), Decimal("0.00"), Decimal("31200.00"), Decimal("26440.68"), Decimal("4759.32"), Decimal("0.00"), Decimal("0.00"), "122024", "N", "Y", "N", ["PERIOD MISMATCH"]),
        ("33AATCR7788M1ZR", "RECO-PART-008", "2025-01-21", Decimal("22400.00"), Decimal("18983.05"), Decimal("0.00"), Decimal("1708.47"), Decimal("1708.47"), Decimal("21900.00"), Decimal("18559.32"), Decimal("0.00"), Decimal("1670.34"), Decimal("1670.34"), "012025", "N", "Y", "N", ["INVOICE VALUE MISMATCH", "TAXABLE VALUE MISMATCH"]),
        ("27AAACB9988C1Z9", "RECO-PART-009", "2025-01-24", Decimal("51000.00"), Decimal("43220.34"), Decimal("7779.66"), Decimal("0.00"), Decimal("0.00"), Decimal("51000.00"), Decimal("43220.34"), Decimal("7779.66"), Decimal("0.00"), Decimal("0.00"), "012025", "N", "N", "N", ["ITC AVAILMENT BLOCKED"]),
        ("33AAFFB3322E1Z2", "RECO-PART-010", "2025-01-27", Decimal("38800.00"), Decimal("32881.36"), Decimal("0.00"), Decimal("2959.32"), Decimal("2959.32"), Decimal("38800.00"), Decimal("32881.36"), Decimal("0.00"), Decimal("2959.32"), Decimal("2959.32"), "012025", "N", "Y", "N", ["INVOICE DATE MISMATCH"]),
    ]

    for gstin, inv_no, inv_date_str, val_2b, txval_2b, igst_2b, cgst_2b, sgst_2b, val_b, txval_b, igst_b, cgst_b, sgst_b, fp_2b, rcm_2b, itc_2b, rcm_b, mismatches in partial_samples:
        d_2b = date.fromisoformat(inv_date_str)
        fp_hash = hashlib.sha256(f"{gstin}|{inv_no}|{inv_date_str}|{val_2b}".encode()).hexdigest()
        inv_2b = GSTR2BInvoice.objects.create(
            gstin=gstin,
            vendor_name="Precision Industrial Corp",
            invoice_no=inv_no,
            invoice_date=d_2b,
            invoice_value=val_2b,
            taxable_value=txval_2b,
            igst=igst_2b,
            cgst=cgst_2b,
            sgst=sgst_2b,
            cess=Decimal('0.00'),
            fingerprint=fp_hash,
            raw_data={'fp': fp_2b, 'period': 'January 2024-25', 'rchrg': rcm_2b, 'itcavl': itc_2b}
        )

        d_books = date(2025, 1, 15) if "INVOICE DATE MISMATCH" in mismatches else d_2b

        pv = VoucherPurchaseSupplierDetails.objects.create(
            date=d_books,
            supplier_invoice_no=inv_no,
            supplier_invoice_date=d_books,
            purchase_voucher_no=f"PV-{inv_no}",
            vendor_name="Precision Industrial Corp",
            vendor_basic_detail=vendor_b,
            gstin=gstin,
            input_type='RCM' if rcm_b == 'Y' else ('Interstate' if igst_b > 0 else 'Intrastate'),
            tenant_id=tenant_id
        )
        VoucherPurchaseItem.objects.create(
            supplier_details=pv,
            item_code='ITEM-PRT',
            item_name='Precision Components Batch',
            quantity=Decimal('1.00'),
            rate=txval_b,
            taxable_value=txval_b,
            igst_amount=igst_b,
            cgst_amount=cgst_b,
            sgst_amount=sgst_b,
            cess_amount=Decimal('0.00'),
            invoice_value=val_b
        )
        VoucherPurchaseDueDetails.objects.create(
            supplier_details=pv,
            to_pay=val_b
        )

        score = 80 if len(mismatches) == 1 else 65
        itc_status = 'NO' if itc_2b == 'N' else 'YES'
        ReconciliationResult.objects.create(
            invoice_2b=inv_2b,
            purchase_voucher_id=pv.id,
            matching_score=score,
            status='PARTIAL',
            matching_details={
                'status': 'PARTIAL',
                'matching_score': score,
                'mismatches': mismatches,
                'itc_availment': itc_status,
                'itc_availability': itc_status,
                'fields': [],
                'books_data': {
                    'purchase_voucher_id': pv.id,
                    'invoice_no': inv_no,
                    'invoice_date': str(d_books),
                    'invoice_value': float(val_b),
                    'taxable_value': float(txval_b),
                    'igst': float(igst_b),
                    'cgst': float(cgst_b),
                    'sgst': float(sgst_b),
                    'vendor_name': "Precision Industrial Corp",
                    'supplier_gstin': gstin,
                    'gstr_period': 'January 2024-25',
                    'reverse_charge': rcm_b,
                    'itc_availability': itc_status,
                }
            }
        )

    # -------------------------------------------------------------
    # 3. MISSING IN BOOKS (10 Records)
    # -------------------------------------------------------------
    print("Seeding 10 MISSING IN BOOKS records...")
    missing_books_samples = [
        ("33AABCU9603R1ZM", "GSTR2B-ONLY-101", "2025-01-03", Decimal("11800.00"), Decimal("10000.00"), Decimal("0.00"), Decimal("900.00"), Decimal("900.00"), "Delta Logistics Global"),
        ("33AACD1234E1ZX", "GSTR2B-ONLY-102", "2025-01-06", Decimal("10000.00"), Decimal("8474.58"), Decimal("1525.42"), Decimal("0.00"), Decimal("0.00"), "Sunrise Tech Engineering"),
        ("33AAABM5678K1ZP", "GSTR2B-ONLY-103", "2025-01-08", Decimal("5900.00"), Decimal("5000.00"), Decimal("0.00"), Decimal("450.00"), Decimal("450.00"), "Pioneer CNC Solutions"),
        ("33AAACR9876L1ZT", "GSTR2B-ONLY-104", "2025-01-11", Decimal("23600.00"), Decimal("20000.00"), Decimal("3600.00"), Decimal("0.00"), Decimal("0.00"), "Metro Pneumatics Ltd"),
        ("27AABCT1234Q1ZA", "GSTR2B-ONLY-105", "2025-01-13", Decimal("11800.00"), Decimal("10000.00"), Decimal("1800.00"), Decimal("0.00"), Decimal("0.00"), "Quantum Sensors & Controls"),
        ("33AAGCB1286Q1ZB", "GSTR2B-ONLY-106", "2025-01-16", Decimal("35400.00"), Decimal("30000.00"), Decimal("0.00"), Decimal("2700.00"), Decimal("2700.00"), "Dynamic Hydraulics Ltd"),
        ("33AALCS5544P1ZU", "GSTR2B-ONLY-107", "2025-01-19", Decimal("17700.00"), Decimal("15000.00"), Decimal("2700.00"), Decimal("0.00"), Decimal("0.00"), "Electra Cabling Solutions"),
        ("33AATCR7788M1ZR", "GSTR2B-ONLY-108", "2025-01-22", Decimal("8260.00"), Decimal("7000.00"), Decimal("0.00"), Decimal("630.00"), Decimal("630.00"), "Vanguard Steels Corp"),
        ("27AAACB9988C1Z9", "GSTR2B-ONLY-109", "2025-01-25", Decimal("47200.00"), Decimal("40000.00"), Decimal("7200.00"), Decimal("0.00"), Decimal("0.00"), "Universal Packing Systems"),
        ("33AAFFB3322E1Z2", "GSTR2B-ONLY-110", "2025-01-28", Decimal("14160.00"), Decimal("12000.00"), Decimal("0.00"), Decimal("1080.00"), Decimal("1080.00"), "Standard Bearings & Alloys"),
    ]

    for gstin, inv_no, inv_date_str, val, txval, igst, cgst, sgst, v_name in missing_books_samples:
        d = date.fromisoformat(inv_date_str)
        fp = hashlib.sha256(f"{gstin}|{inv_no}|{inv_date_str}|{val}".encode()).hexdigest()
        inv_2b = GSTR2BInvoice.objects.create(
            gstin=gstin,
            vendor_name=v_name,
            invoice_no=inv_no,
            invoice_date=d,
            invoice_value=val,
            taxable_value=txval,
            igst=igst,
            cgst=cgst,
            sgst=sgst,
            cess=Decimal('0.00'),
            fingerprint=fp,
            raw_data={'fp': '012025', 'period': 'January 2024-25', 'rchrg': 'N', 'itcavl': 'Y'}
        )

        ReconciliationResult.objects.create(
            invoice_2b=inv_2b,
            purchase_voucher_id=None,
            matching_score=0,
            status='MISSING_BOOKS',
            matching_details={
                'status': 'MISSING_BOOKS',
                'matching_score': 0,
                'mismatches': ['Missing in Books (No purchase voucher found)'],
                'itc_availment': 'YES',
                'itc_availability': 'YES',
                'fields': []
            }
        )

    # -------------------------------------------------------------
    # 4. MISSING IN 2B (10 Records)
    # -------------------------------------------------------------
    print("Seeding 10 MISSING IN 2B records...")
    missing_2b_samples = [
        ("33AAKCS1122D1ZV", "RECO-MISS2B-001", "2025-01-02", Decimal("12980.00"), Decimal("11000.00"), Decimal("0.00"), Decimal("990.00"), Decimal("990.00"), "Bharat Heavy Fabrication"),
        ("33AAMCT3344F1ZT", "RECO-MISS2B-002", "2025-01-05", Decimal("21240.00"), Decimal("18000.00"), Decimal("3240.00"), Decimal("0.00"), Decimal("0.00"), "Titan Cutting Tools Ltd"),
        ("33AANCR5566G1ZR", "RECO-MISS2B-003", "2025-01-08", Decimal("7080.00"), Decimal("6000.00"), Decimal("0.00"), Decimal("540.00"), Decimal("540.00"), "Maruti Fasteners & Bolts"),
        ("27AAPCM7788H1ZP", "RECO-MISS2B-004", "2025-01-11", Decimal("38940.00"), Decimal("33000.00"), Decimal("5940.00"), Decimal("0.00"), Decimal("0.00"), "Western Precision Foundry"),
        ("33AAQCB9900J1ZN", "RECO-MISS2B-005", "2025-01-14", Decimal("16520.00"), Decimal("14000.00"), Decimal("0.00"), Decimal("1260.00"), Decimal("1260.00"), "Southern Electricals & Wiring"),
        ("33AARCL2233K1ZL", "RECO-MISS2B-006", "2025-01-17", Decimal("53100.00"), Decimal("45000.00"), Decimal("8100.00"), Decimal("0.00"), Decimal("0.00"), "National Abrasives Corp"),
        ("33AASCS4455L1ZJ", "RECO-MISS2B-007", "2025-01-20", Decimal("9440.00"), Decimal("8000.00"), Decimal("0.00"), Decimal("720.00"), Decimal("720.00"), "Chennai Rubber & Seals"),
        ("27AATCT6677M1ZH", "RECO-MISS2B-008", "2025-01-23", Decimal("44840.00"), Decimal("38000.00"), Decimal("6840.00"), Decimal("0.00"), Decimal("0.00"), "Bombay Chemical Reagents"),
        ("33AAUCR8899N1ZF", "RECO-MISS2B-009", "2025-01-26", Decimal("25960.00"), Decimal("22000.00"), Decimal("0.00"), Decimal("1980.00"), Decimal("1980.00"), "Supreme Lubricants Pvt Ltd"),
        ("33AAVCB1122P1ZD", "RECO-MISS2B-010", "2025-01-29", Decimal("64900.00"), Decimal("55000.00"), Decimal("9900.00"), Decimal("0.00"), Decimal("0.00"), "Matrix Automation Systems"),
    ]

    for gstin, inv_no, inv_date_str, val, txval, igst, cgst, sgst, v_name in missing_2b_samples:
        d = date.fromisoformat(inv_date_str)
        pv = VoucherPurchaseSupplierDetails.objects.create(
            date=d,
            supplier_invoice_no=inv_no,
            supplier_invoice_date=d,
            purchase_voucher_no=f"PV-{inv_no}",
            vendor_name=v_name,
            vendor_basic_detail=vendor_c,
            gstin=gstin,
            input_type='Interstate' if igst > 0 else 'Intrastate',
            tenant_id=tenant_id
        )
        VoucherPurchaseItem.objects.create(
            supplier_details=pv,
            item_code='ITEM-MIS2B',
            item_name='Industrial Consumables & Supplies',
            quantity=Decimal('1.00'),
            rate=txval,
            taxable_value=txval,
            igst_amount=igst,
            cgst_amount=cgst,
            sgst_amount=sgst,
            cess_amount=Decimal('0.00'),
            invoice_value=val
        )
        VoucherPurchaseDueDetails.objects.create(
            supplier_details=pv,
            to_pay=val
        )

        ReconciliationResult.objects.create(
            invoice_2b=None,
            purchase_voucher_id=pv.id,
            matching_score=0,
            status='MISSING_2B',
            matching_details={
                'status': 'MISSING_2B',
                'matching_score': 0,
                'mismatches': ['Missing in GSTR-2B (Supplier has not filed invoice)'],
                'itc_availment': 'NO',
                'itc_availability': 'NO',
                'books_data': {
                    'purchase_voucher_id': pv.id,
                    'invoice_no': inv_no,
                    'invoice_date': inv_date_str,
                    'invoice_value': float(val),
                    'taxable_value': float(txval),
                    'igst': float(igst),
                    'cgst': float(cgst),
                    'sgst': float(sgst),
                    'vendor_name': v_name,
                    'supplier_gstin': gstin,
                    'gstr_period': 'January 2024-25',
                    'reverse_charge': 'N',
                    'itc_availability': 'YES',
                }
            }
        )

    print("\n[SUCCESS] Seeding Complete!")
    print(f"Total Exact Match: {ReconciliationResult.objects.filter(status='EXACT').count()}")
    print(f"Total Partial / Mismatch: {ReconciliationResult.objects.filter(status__in=['PARTIAL', 'MISMATCH']).count()}")
    print(f"Total Missing in Books: {ReconciliationResult.objects.filter(status='MISSING_BOOKS').count()}")
    print(f"Total Missing in 2B: {ReconciliationResult.objects.filter(status='MISSING_2B').count()}")
    print(f"Total Results: {ReconciliationResult.objects.count()}")

if __name__ == '__main__':
    seed_reconciliation()
