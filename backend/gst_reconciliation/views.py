import hashlib
import json
import threading
from datetime import timedelta
from decimal import Decimal
from django.db.models import Q, Sum
from django.utils import timezone
from .models import (
    GSTR2BInvoice, ReconciliationResult, AuditLog, 
    ITCSummary, GSTR3BReport, GSTJobStatus, ValidationResult,
    GSTLateFee, GSTElectronicLedger
)
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from accounting.models_voucher_sales import VoucherSalesInvoiceDetails
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    GSTR2BInvoiceSerializer, ReconciliationResultSerializer, 
    ITCSummarySerializer, GSTR3BReportSerializer, AuditLogSerializer
)
from .services import GSTValidationService
from .sandbox_service import SandboxGSTService

class GSTReconciliationViewSet(viewsets.ViewSet):
    """
    Main controller for GST Reconciliation, ITC, and GSTR-3B logic.
    Supports asynchronous-style background processing via JobStatus.
    """

    @action(detail=False, methods=['post'])
    def upload_2b(self, request):
        """Module 1: Ingest GSTR-2B JSON data (supports raw lists or full GSTR-2B dict structures)."""
        data = request.data
        invoices = self._extract_invoices_from_payload(data)

        if not invoices:
            return Response({"error": "No valid GSTR-2B invoices found in payload."}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        duplicate_count = 0

        for inv in invoices:
            try:
                gstin = self._normalize_gstin(inv.get('gstin', ''))
                inv_no = self._normalize_inv_no(inv.get('invoice_no', ''))
                inv_date = self._normalize_date(inv.get('invoice_date'))
                inv_val = Decimal(str(inv.get('invoice_value', 0)))
                
                raw_str = f"{gstin}|{inv_no}|{inv_date}|{inv_val}"
                fingerprint = hashlib.sha256(raw_str.encode()).hexdigest()

                if GSTR2BInvoice.objects.filter(fingerprint=fingerprint).exists():
                    duplicate_count += 1
                    continue

                GSTR2BInvoice.objects.create(
                    gstin=gstin,
                    vendor_name=inv.get('vendor_name'),
                    invoice_no=inv_no,
                    invoice_date=inv_date,
                    invoice_value=inv_val,
                    taxable_value=Decimal(str(inv.get('taxable_value', 0))),
                    igst=Decimal(str(inv.get('igst', 0))),
                    cgst=Decimal(str(inv.get('cgst', 0))),
                    sgst=Decimal(str(inv.get('sgst', 0))),
                    cess=Decimal(str(inv.get('cess', 0))),
                    fingerprint=fingerprint,
                    raw_data=inv.get('raw_data') or inv
                )
                created_count += 1
            except Exception:
                continue

        AuditLog.objects.create(
            action="GSTR-2B Upload",
            details={"created": created_count, "duplicates": duplicate_count},
            executed_by=str(request.user)
        )

        return Response({"message": "Upload complete", "created": created_count, "duplicates": duplicate_count})

    def list_invoices(self, request):
        """
        Returns raw GSTR-2B government invoices filtered by month and year.
        Used by the GSTR-2B sub-tab inside GSTR2 – Inward Supplies.
        Does NOT touch reconciliation logic.

        Query params:
          month  – e.g. "August"
          year   – e.g. "2026-27"
        """
        query_params = getattr(request, 'query_params', request.GET)
        month_str = query_params.get('month', '')
        year_str = query_params.get('year', '')

        qs = GSTR2BInvoice.objects.all()

        # Apply tenant filter when present
        user = getattr(request, 'user', None)
        tenant_id = getattr(user, 'tenant_id', None) if user else None


        # Period filter
        period = self._normalize_reco_period(month_str, year_str)
        if period:
            m_num, cal_yr = period
            qs = qs.filter(invoice_date__month=m_num, invoice_date__year=cal_yr)

        qs = qs.order_by('-invoice_date')

        data = []
        for inv in qs:
            data.append({
                'id': inv.id,
                'gstin': inv.gstin,
                'supplier_name': inv.vendor_name or '',
                'invoice_no': inv.invoice_no,
                'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else '',
                'invoice_value': float(inv.invoice_value),
                'taxable_value': float(inv.taxable_value),
                'igst': float(inv.igst),
                'cgst': float(inv.cgst),
                'sgst': float(inv.sgst),
                'cess': float(inv.cess),
                'place_of_supply': inv.raw_data.get('place_of_supply', '') if isinstance(inv.raw_data, dict) else '',
            })

        return Response({'count': len(data), 'invoices': data})

    def _normalize_date(self, date_val):
        if not date_val:
            return timezone.now().date().isoformat()
        if hasattr(date_val, 'isoformat'):
            return date_val.isoformat()
        date_str = str(date_val).strip()
        from datetime import datetime
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%d-%B-%Y', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                return datetime.strptime(date_str, fmt).date().isoformat()
            except ValueError:
                pass
        try:
            return date_str.split('T')[0]
        except Exception:
            return timezone.now().date().isoformat()

    def _normalize_gstin(self, gstin):
        if not gstin:
            return ""
        return str(gstin).strip().upper()

    def _normalize_inv_no(self, inv_no):
        if not inv_no:
            return ""
        import re
        s = str(inv_no).strip().upper()
        return re.sub(r'\s+', ' ', s)

    def _normalize_period(self, period_str):
        """
        Parses various period representations into (month_int, calendar_year_int).
        Examples: '072026' -> (7, 2026), '2026-07' -> (7, 2026), 'July 2026' -> (7, 2026)
        """
        if not period_str:
            return None
        import re
        s = str(period_str).strip()
        
        # MMYYYY or MYYYY
        m_mmyyyy = re.match(r'^(\d{1,2})(\d{4})$', s)
        if m_mmyyyy:
            m_val = int(m_mmyyyy.group(1))
            y_val = int(m_mmyyyy.group(2))
            if 1 <= m_val <= 12:
                return (m_val, y_val)

        # YYYY-MM or YYYY/MM
        m_yyyymm = re.match(r'^(\d{4})[-/](\d{1,2})$', s)
        if m_yyyymm:
            y_val = int(m_yyyymm.group(1))
            m_val = int(m_yyyymm.group(2))
            if 1 <= m_val <= 12:
                return (m_val, y_val)

        # MM-YYYY or MM/YYYY
        m_mmyyyy_slash = re.match(r'^(\d{1,2})[-/](\d{4})$', s)
        if m_mmyyyy_slash:
            m_val = int(m_mmyyyy_slash.group(1))
            y_val = int(m_mmyyyy_slash.group(2))
            if 1 <= m_val <= 12:
                return (m_val, y_val)

        # Month name + year e.g. "July 2026"
        month_names = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        for name, num in month_names.items():
            if name in s.lower():
                m_year = re.search(r'\b(\d{4})\b', s)
                if m_year:
                    return (num, int(m_year.group(1)))
        return None

    def _normalize_reco_period(self, month_str, year_str):
        """
        Converts reconciliation month and year (e.g. Month='July', Year='2026-27' or '2026')
        into (month_int, calendar_year_int).
        """
        if not month_str or not year_str:
            return None
        month_map = {
            'January': 1, 'February': 2, 'March': 3,
            'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9,
            'October': 10, 'November': 11, 'December': 12
        }
        m_num = month_map.get(str(month_str).strip().capitalize(), None)
        if not m_num:
            try:
                m_num = int(month_str)
            except Exception:
                return None

        y_str = str(year_str).strip()
        if '-' in y_str:
            start_yr = int(y_str.split('-')[0])
            # In Indian FY (April-March): Apr-Dec = start_yr, Jan-Mar = start_yr + 1
            cal_yr = start_yr if m_num >= 4 else (start_yr + 1)
        else:
            try:
                cal_yr = int(y_str)
            except Exception:
                return None

        return (m_num, cal_yr)

    def _extract_invoices_from_payload(self, payload):
        extracted = []
        docdata_fp = ''
        if isinstance(payload, list):
            items_to_process = payload
        elif isinstance(payload, dict):
            docdata_fp = payload.get('fp') or payload.get('data', {}).get('fp') or payload.get('period') or ''
            docdata = payload.get('data', {}).get('docdata') or payload.get('docdata') or payload.get('data') or payload
            items_to_process = []
            if isinstance(docdata, dict):
                if not docdata_fp:
                    docdata_fp = docdata.get('fp') or ''
                for sec in ['b2b', 'b2ba', 'cdnr', 'cdnra', 'invoices', 'items', 'records']:
                    sec_data = docdata.get(sec)
                    if isinstance(sec_data, list):
                        items_to_process.extend(sec_data)
            elif isinstance(docdata, list):
                items_to_process = docdata
            else:
                items_to_process = [payload]
        else:
            return []

        for item in items_to_process:
            if not isinstance(item, dict):
                continue
            
            ctin = self._normalize_gstin(item.get('ctin') or item.get('gstin') or item.get('Supplier GSTIN') or '')
            trdnm = item.get('trdnm') or item.get('trade_name') or item.get('vendor_name') or item.get('Supplier Name') or item.get('cfs') or ''
            item_fp = item.get('fp') or item.get('period') or item.get('Filing Period') or docdata_fp or ''
            inv_list = item.get('inv') or item.get('invoices') or item.get('nt')
            
            if isinstance(inv_list, list):
                for inv_item in inv_list:
                    if not isinstance(inv_item, dict):
                        continue
                    inv_no = self._normalize_inv_no(inv_item.get('inum') or inv_item.get('invoice_no') or inv_item.get('nt_num') or inv_item.get('Invoice Number') or inv_item.get('doc_no') or '')
                    inv_date = self._normalize_date(inv_item.get('dt') or inv_item.get('idt') or inv_item.get('invoice_date') or inv_item.get('nt_dt') or inv_item.get('Invoice Date') or inv_item.get('date'))
                    inv_val = inv_item.get('val') or inv_item.get('invoice_value') or inv_item.get('Invoice Value') or inv_item.get('total_amount') or 0
                    
                    line_items = inv_item.get('items') or []
                    txval = sum(Decimal(str(it.get('txval', 0) or it.get('taxable_value', 0) or it.get('Taxable Value', 0) or 0)) for it in line_items if isinstance(it, dict))
                    igst = sum(Decimal(str(it.get('iamt', 0) or it.get('igst', 0) or it.get('IGST', 0) or 0)) for it in line_items if isinstance(it, dict))
                    cgst = sum(Decimal(str(it.get('camt', 0) or it.get('cgst', 0) or it.get('CGST', 0) or 0)) for it in line_items if isinstance(it, dict))
                    sgst = sum(Decimal(str(it.get('samt', 0) or it.get('sgst', 0) or it.get('SGST', 0) or 0)) for it in line_items if isinstance(it, dict))
                    cess = sum(Decimal(str(it.get('csamt', 0) or it.get('cess', 0) or it.get('CESS', 0) or 0)) for it in line_items if isinstance(it, dict))
                    
                    if not txval and (inv_item.get('txval') or inv_item.get('taxable_value') or inv_item.get('Taxable Value')):
                        txval = Decimal(str(inv_item.get('txval') or inv_item.get('taxable_value') or inv_item.get('Taxable Value') or 0))
                    if not igst and (inv_item.get('iamt') or inv_item.get('igst') or inv_item.get('IGST')):
                        igst = Decimal(str(inv_item.get('iamt') or inv_item.get('igst') or inv_item.get('IGST') or 0))
                    if not cgst and (inv_item.get('camt') or inv_item.get('cgst') or inv_item.get('CGST')):
                        cgst = Decimal(str(inv_item.get('camt') or inv_item.get('cgst') or inv_item.get('CGST') or 0))
                    if not sgst and (inv_item.get('samt') or inv_item.get('sgst') or inv_item.get('SGST')):
                        sgst = Decimal(str(inv_item.get('samt') or inv_item.get('sgst') or inv_item.get('SGST') or 0))
                    if not cess and (inv_item.get('csamt') or inv_item.get('cess') or inv_item.get('CESS')):
                        cess = Decimal(str(inv_item.get('csamt') or inv_item.get('cess') or inv_item.get('CESS') or 0))

                    inv_raw = dict(inv_item)
                    inv_raw['fp'] = inv_item.get('fp') or item_fp
                    inv_raw['rchrg'] = inv_item.get('rchrg') or inv_item.get('rev') or inv_item.get('reverse_charge') or inv_item.get('Reverse Charge') or item.get('rchrg') or 'N'
                    inv_raw['itcavl'] = inv_item.get('itcavl') or inv_item.get('itc_avl') or inv_item.get('itc_availment') or inv_item.get('ITC Eligible') or inv_item.get('itc') or item.get('itcavl') or 'Y'
                    inv_raw['ctin'] = ctin
                    inv_raw['trdnm'] = trdnm

                    extracted.append({
                        'gstin': ctin,
                        'vendor_name': trdnm,
                        'invoice_no': inv_no,
                        'invoice_date': inv_date,
                        'invoice_value': Decimal(str(inv_val)),
                        'taxable_value': txval,
                        'igst': igst,
                        'cgst': cgst,
                        'sgst': sgst,
                        'cess': cess,
                        'raw_data': inv_raw,
                    })
            else:
                inv_no = self._normalize_inv_no(item.get('invoice_no') or item.get('inum') or item.get('inv_no') or item.get('Invoice Number') or item.get('doc_no') or '')
                inv_date = self._normalize_date(item.get('dt') or item.get('invoice_date') or item.get('idt') or item.get('Invoice Date') or item.get('date'))
                inv_val = item.get('invoice_value') or item.get('val') or item.get('Invoice Value') or item.get('total_amount') or 0
                txval = item.get('taxable_value') or item.get('txval') or item.get('Taxable Value') or 0
                igst = item.get('igst') or item.get('iamt') or item.get('IGST') or 0
                cgst = item.get('cgst') or item.get('camt') or item.get('CGST') or 0
                sgst = item.get('sgst') or item.get('samt') or item.get('SGST') or 0
                cess = item.get('cess') or item.get('csamt') or item.get('CESS') or 0

                item_raw = dict(item)
                item_raw['fp'] = item.get('fp') or item.get('period') or item.get('Filing Period') or docdata_fp or ''
                item_raw['rchrg'] = item.get('rchrg') or item.get('rev') or item.get('reverse_charge') or item.get('Reverse Charge') or 'N'
                item_raw['itcavl'] = item.get('itcavl') or item.get('itc_avl') or item.get('itc_availment') or item.get('ITC Eligible') or item.get('itc') or 'Y'
                item_raw['ctin'] = ctin
                item_raw['trdnm'] = trdnm or item.get('vendor_name') or ''
                
                extracted.append({
                    'gstin': ctin,
                    'vendor_name': trdnm or item.get('vendor_name') or '',
                    'invoice_no': inv_no,
                    'invoice_date': inv_date,
                    'invoice_value': Decimal(str(inv_val)),
                    'taxable_value': Decimal(str(txval)),
                    'igst': Decimal(str(igst)),
                    'cgst': Decimal(str(cgst)),
                    'sgst': Decimal(str(sgst)),
                    'cess': Decimal(str(cess)),
                    'raw_data': item_raw,
                })

        return extracted

    def _validate_invoice_against_voucher(self, inv_2b, v, reco_month, reco_year):
        """
        Executes strict 12-field validation between GSTR-2B and candidate Purchase Voucher.
        """
        mismatches = []
        field_results = []
        TOLERANCE = Decimal('1.00')

        # 1. Supplier GSTIN
        gstin_2b = self._normalize_gstin(inv_2b.gstin)
        gstin_books = self._normalize_gstin(v.gstin)
        if gstin_2b and gstin_books and gstin_2b == gstin_books:
            field_results.append({"field": "Supplier GSTIN", "gstr2b": gstin_2b, "books": gstin_books, "status": "MATCH"})
        else:
            mismatches.append("GSTIN MISMATCH")
            field_results.append({"field": "Supplier GSTIN", "gstr2b": gstin_2b, "books": gstin_books, "status": "MISMATCH"})

        # 2. Invoice Number
        inv_no_2b = self._normalize_inv_no(inv_2b.invoice_no)
        inv_no_books = self._normalize_inv_no(v.supplier_invoice_no or v.purchase_voucher_no or '')
        if inv_no_2b and inv_no_books and inv_no_2b == inv_no_books:
            field_results.append({"field": "Invoice Number", "gstr2b": inv_2b.invoice_no, "books": v.supplier_invoice_no or v.purchase_voucher_no, "status": "MATCH"})
        else:
            mismatches.append("INVOICE NUMBER MISMATCH")
            field_results.append({"field": "Invoice Number", "gstr2b": inv_2b.invoice_no, "books": v.supplier_invoice_no or v.purchase_voucher_no, "status": "MISMATCH"})

        # 3. Invoice Date
        raw_date_2b = (inv_2b.raw_data or {}).get('dt') or (inv_2b.raw_data or {}).get('idt') or (inv_2b.raw_data or {}).get('Invoice Date') or inv_2b.invoice_date
        date_2b_norm = self._normalize_date(raw_date_2b)
        raw_date_books = v.supplier_invoice_date or v.date
        date_books_norm = self._normalize_date(raw_date_books)

        if date_2b_norm == date_books_norm:
            field_results.append({"field": "Invoice Date", "gstr2b": date_2b_norm, "books": date_books_norm, "status": "MATCH"})
        else:
            mismatches.append("INVOICE DATE MISMATCH")
            field_results.append({"field": "Invoice Date", "gstr2b": date_2b_norm, "books": date_books_norm, "status": "MISMATCH"})

        # Books financial totals from line items
        line_items = list(v.line_items.all())
        books_txval = sum(Decimal(str(item.taxable_value or 0)) for item in line_items)
        books_igst = sum(Decimal(str(item.igst_amount or 0)) for item in line_items)
        books_cgst = sum(Decimal(str(item.cgst_amount or 0)) for item in line_items)
        books_sgst = sum(Decimal(str(item.sgst_amount or 0)) for item in line_items)
        books_cess = sum(Decimal(str(item.cess_amount or 0)) for item in line_items)

        books_inv_val = sum(Decimal(str(item.invoice_value or 0)) for item in line_items)
        if books_inv_val == Decimal('0'):
            books_inv_val = books_txval + books_igst + books_cgst + books_sgst + books_cess
        if books_inv_val == Decimal('0'):
            books_inv_val = Decimal(str(getattr(getattr(v, 'due_details', None), 'to_pay', 0) or 0))

        # 4. Invoice Actual / Invoice Value
        val_2b = Decimal(str(inv_2b.invoice_value or 0))
        val_diff = val_2b - books_inv_val
        if abs(val_diff) <= TOLERANCE:
            field_results.append({"field": "Invoice Value", "gstr2b": float(val_2b), "books": float(books_inv_val), "difference": float(val_diff), "status": "MATCH"})
        else:
            mismatches.append("INVOICE VALUE MISMATCH")
            field_results.append({"field": "Invoice Value", "gstr2b": float(val_2b), "books": float(books_inv_val), "difference": float(val_diff), "status": "MISMATCH"})

        # 5. Taxable Value
        txval_2b = Decimal(str(inv_2b.taxable_value or 0))
        txval_diff = txval_2b - books_txval
        if abs(txval_diff) <= TOLERANCE:
            field_results.append({"field": "Taxable Value", "gstr2b": float(txval_2b), "books": float(books_txval), "difference": float(txval_diff), "status": "MATCH"})
        else:
            mismatches.append("TAXABLE VALUE MISMATCH")
            field_results.append({"field": "Taxable Value", "gstr2b": float(txval_2b), "books": float(books_txval), "difference": float(txval_diff), "status": "MISMATCH"})

        # 6. IGST
        igst_2b = Decimal(str(inv_2b.igst or 0))
        igst_diff = igst_2b - books_igst
        if abs(igst_diff) <= TOLERANCE:
            field_results.append({"field": "IGST", "gstr2b": float(igst_2b), "books": float(books_igst), "difference": float(igst_diff), "status": "MATCH"})
        else:
            mismatches.append("IGST MISMATCH")
            field_results.append({"field": "IGST", "gstr2b": float(igst_2b), "books": float(books_igst), "difference": float(igst_diff), "status": "MISMATCH"})

        # 7. CGST
        cgst_2b = Decimal(str(inv_2b.cgst or 0))
        cgst_diff = cgst_2b - books_cgst
        if abs(cgst_diff) <= TOLERANCE:
            field_results.append({"field": "CGST", "gstr2b": float(cgst_2b), "books": float(books_cgst), "difference": float(cgst_diff), "status": "MATCH"})
        else:
            mismatches.append("CGST MISMATCH")
            field_results.append({"field": "CGST", "gstr2b": float(cgst_2b), "books": float(books_cgst), "difference": float(cgst_diff), "status": "MISMATCH"})

        # 8. SGST
        sgst_2b = Decimal(str(inv_2b.sgst or 0))
        sgst_diff = sgst_2b - books_sgst
        if abs(sgst_diff) <= TOLERANCE:
            field_results.append({"field": "SGST", "gstr2b": float(sgst_2b), "books": float(books_sgst), "difference": float(sgst_diff), "status": "MATCH"})
        else:
            mismatches.append("SGST MISMATCH")
            field_results.append({"field": "SGST", "gstr2b": float(sgst_2b), "books": float(books_sgst), "difference": float(sgst_diff), "status": "MISMATCH"})

        # 9. GSTR-2B Period
        period_2b_raw = (inv_2b.raw_data or {}).get('fp') or (inv_2b.raw_data or {}).get('period') or (inv_2b.raw_data or {}).get('Filing Period') or (inv_2b.raw_data or {}).get('gstr2b_period') or (inv_2b.raw_data or {}).get('return_period')
        norm_period_2b = self._normalize_period(period_2b_raw) if period_2b_raw else None
        norm_reco_period = self._normalize_reco_period(reco_month, reco_year)

        if norm_period_2b is None or norm_reco_period is None or norm_period_2b == norm_reco_period:
            field_results.append({"field": "GSTR-2B Period", "gstr2b": period_2b_raw or f"{reco_month} {reco_year}", "books": f"{reco_month} {reco_year}", "status": "MATCH"})
        else:
            mismatches.append("PERIOD MISMATCH")
            field_results.append({"field": "GSTR-2B Period", "gstr2b": period_2b_raw, "books": f"{reco_month} {reco_year}", "status": "MISMATCH"})

        # 10. Total Value
        tot_val_2b = Decimal(str((inv_2b.raw_data or {}).get('val') or (inv_2b.raw_data or {}).get('Invoice Value') or inv_2b.invoice_value or 0))
        tot_diff = tot_val_2b - books_inv_val
        if abs(tot_diff) <= TOLERANCE:
            field_results.append({"field": "Total Value", "gstr2b": float(tot_val_2b), "books": float(books_inv_val), "difference": float(tot_diff), "status": "MATCH"})
        else:
            mismatches.append("TOTAL VALUE MISMATCH")
            field_results.append({"field": "Total Value", "gstr2b": float(tot_val_2b), "books": float(books_inv_val), "difference": float(tot_diff), "status": "MISMATCH"})

        # 11. Reverse Charge
        rcm_2b_raw = (inv_2b.raw_data or {}).get('rchrg') or (inv_2b.raw_data or {}).get('rev') or (inv_2b.raw_data or {}).get('reverse_charge') or (inv_2b.raw_data or {}).get('Reverse Charge') or 'N'
        rcm_2b_bool = True if str(rcm_2b_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1') else False
        rcm_books_raw = getattr(v, 'reverse_charge', None) or getattr(v, 'is_rcm', None) or getattr(v, 'rcm', None) or ('Y' if getattr(v, 'input_type', '') == 'RCM' else 'N')
        rcm_books_bool = True if str(rcm_books_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1') else False

        if rcm_2b_bool == rcm_books_bool:
            field_results.append({"field": "Reverse Charge", "gstr2b": "Y" if rcm_2b_bool else "N", "books": "Y" if rcm_books_bool else "N", "status": "MATCH"})
        else:
            mismatches.append("REVERSE CHARGE MISMATCH")
            field_results.append({"field": "Reverse Charge", "gstr2b": "Y" if rcm_2b_bool else "N", "books": "Y" if rcm_books_bool else "N", "status": "MISMATCH"})

        # 12. ITC Availability
        itc_raw = (inv_2b.raw_data or {}).get('itcavl') or (inv_2b.raw_data or {}).get('itc_avl') or (inv_2b.raw_data or {}).get('itc_availment') or (inv_2b.raw_data or {}).get('itc_availability') or (inv_2b.raw_data or {}).get('ITC Eligible') or (inv_2b.raw_data or {}).get('itc') or 'Y'
        itc_availment = 'YES' if str(itc_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1') else 'NO'
        
        if itc_availment == 'NO':
            mismatches.append("ITC AVAILMENT BLOCKED")
            field_results.append({
                "field": "ITC Availability",
                "gstr2b": "NO (Blocked)",
                "books": "NO (Blocked)",
                "status": "BLOCKED",
                "message": "Your ITC Availment is blocked in GSTR-2B"
            })
        else:
            field_results.append({"field": "ITC Availability", "gstr2b": "YES", "books": "YES", "status": "MATCH"})

        # Final decision: 100% match => EXACT, otherwise PARTIAL
        if len(mismatches) == 0:
            status_label = 'EXACT'
            score = 100
        else:
            status_label = 'PARTIAL'
            passed = len(field_results) - len(mismatches)
            score = max(0, int((passed / len(field_results)) * 100))

        return {
            "status": status_label,
            "matching_score": score,
            "mismatches": mismatches,
            "fields": field_results,
            "itc_availment": itc_availment,
            "itc_availability": itc_availment,
            "books_data": {
                "purchase_voucher_id": v.id,
                "invoice_no": v.supplier_invoice_no or v.purchase_voucher_no,
                "invoice_date": date_books_norm,
                "invoice_value": float(books_inv_val),
                "taxable_value": float(books_txval),
                "igst": float(books_igst),
                "cgst": float(books_cgst),
                "sgst": float(books_sgst),
                "cess": float(books_cess),
                "vendor_name": v.vendor_name,
                "supplier_gstin": v.gstin or '',
                "reverse_charge": "Y" if rcm_books_bool else "N",
                "itc_availability": itc_availment,
            }
        }

    def _run_matching_engine(self, tenant_id, month, year, job=None):
        from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
        invoices_2b = GSTR2BInvoice.objects.all()
        if tenant_id:
            vouchers_books = VoucherPurchaseSupplierDetails.objects.filter(
                Q(tenant_id=tenant_id) | Q(tenant_id='default-tenant') | Q(tenant_id__isnull=True) | Q(tenant_id='')
            )
            if not vouchers_books.exists():
                vouchers_books = VoucherPurchaseSupplierDetails.objects.all()
        else:
            vouchers_books = VoucherPurchaseSupplierDetails.objects.all()
        total = invoices_2b.count()
        
        matched_voucher_ids = set()
        for index, inv_2b in enumerate(invoices_2b):
            norm_gstin = self._normalize_gstin(inv_2b.gstin)
            norm_inv_no = self._normalize_inv_no(inv_2b.invoice_no)
            
            candidate = None
            if norm_gstin and norm_inv_no:
                # Primary search using Supplier GSTIN + Invoice Number only
                candidate_qs = vouchers_books.filter(
                    gstin__iexact=norm_gstin
                ).filter(
                    Q(supplier_invoice_no__iexact=norm_inv_no) |
                    Q(normalized_invoice_no__iexact=norm_inv_no) |
                    Q(purchase_voucher_no__iexact=norm_inv_no)
                )
                candidate = candidate_qs.first()
                
                # In-memory whitespace-normalized fallback
                if not candidate:
                    gstin_matches = vouchers_books.filter(gstin__iexact=norm_gstin)
                    for v in gstin_matches:
                        if self._normalize_inv_no(v.supplier_invoice_no or v.purchase_voucher_no or '') == norm_inv_no:
                            candidate = v
                            break

            if candidate:
                matched_voucher_ids.add(candidate.id)
                # Candidate found: run complete 12-field validation
                val_result = self._validate_invoice_against_voucher(inv_2b, candidate, month, year)
                ReconciliationResult.objects.update_or_create(
                    invoice_2b=inv_2b,
                    defaults={
                        'purchase_voucher_id': candidate.id,
                        'matching_score': val_result['matching_score'],
                        'status': val_result['status'],
                        'matching_details': val_result
                    }
                )
            else:
                # No candidate voucher found using Supplier GSTIN + Invoice Number
                raw_itc = (inv_2b.raw_data or {}).get('itcavl') or (inv_2b.raw_data or {}).get('itc_avl') or (inv_2b.raw_data or {}).get('itc_availment') or (inv_2b.raw_data or {}).get('ITC Eligible') or 'Y'
                itc_availment = 'YES' if str(raw_itc).strip().upper() in ('Y', 'YES', 'TRUE', '1') else 'NO'
                mismatches_list = ['Missing in Books']
                if itc_availment == 'NO':
                    mismatches_list.append('ITC Availment is Blocked')
                ReconciliationResult.objects.update_or_create(
                    invoice_2b=inv_2b,
                    defaults={
                        'purchase_voucher_id': None,
                        'matching_score': 0,
                        'status': 'MISSING_BOOKS',
                        'matching_details': {
                            'status': 'MISSING_BOOKS',
                            'matching_score': 0,
                            'mismatches': mismatches_list,
                            'itc_availment': itc_availment,
                            'itc_availability': itc_availment,
                            'fields': []
                        }
                    }
                )
            
            if job and total > 0 and index % 10 == 0:
                job.progress = int((index / total) * 100)
                job.save()

        # Handle vouchers in books not present in 2B (MISSING_2B)
        norm_period = self._normalize_reco_period(month, year)
        for v in vouchers_books:
            if v.id in matched_voucher_ids:
                continue
            
            # If period filter is supplied, check voucher date alignment
            if norm_period and v.date:
                v_month = v.date.month
                v_year = v.date.year
                if (v_month, v_year) != norm_period:
                    inv_d = v.supplier_invoice_date
                    if not (inv_d and (inv_d.month, inv_d.year) == norm_period):
                        continue

            line_items = list(v.line_items.all())
            items_val = sum(Decimal(str(item.invoice_value or item.taxable_value or (item.rate * item.quantity) or 0)) for item in line_items)
            tx_val = sum(Decimal(str(item.taxable_value or 0)) for item in line_items)
            igst_val = sum(Decimal(str(item.igst_amount or 0)) for item in line_items)
            cgst_val = sum(Decimal(str(item.cgst_amount or 0)) for item in line_items)
            sgst_val = sum(Decimal(str(item.sgst_amount or 0)) for item in line_items)
            cess_val = sum(Decimal(str(item.cess_amount or 0)) for item in line_items)
            if items_val == Decimal('0'):
                items_val = Decimal(str(getattr(getattr(v, 'due_details', None), 'to_pay', 0) or 0))
            raw_date = getattr(v, 'supplier_invoice_date', None) or getattr(v, 'date', None)
            
            ReconciliationResult.objects.update_or_create(
                purchase_voucher_id=v.id,
                invoice_2b=None,
                defaults={
                    'matching_score': 0,
                    'status': 'MISSING_2B',
                    'matching_details': {
                        'status': 'MISSING_2B',
                        'matching_score': 0,
                        'mismatches': ['Missing in GSTR-2B (Supplier has not filed invoice)'],
                        'itc_availment': 'NO',
                        'itc_availability': 'NO',
                        'books_data': {
                            'purchase_voucher_id': v.id,
                            'invoice_no': getattr(v, 'supplier_invoice_no', '') or getattr(v, 'purchase_voucher_no', ''),
                            'invoice_date': str(raw_date) if raw_date else '',
                            'invoice_value': float(items_val),
                            'taxable_value': float(tx_val),
                            'igst': float(igst_val),
                            'cgst': float(cgst_val),
                            'sgst': float(sgst_val),
                            'cess': float(cess_val),
                            'vendor_name': getattr(v, 'vendor_name', ''),
                            'supplier_gstin': v.gstin or '',
                            'gstr_period': f"{month} {year}",
                            'reverse_charge': "Y" if (getattr(v, 'input_type', '') == 'RCM' or getattr(v, 'reverse_charge', None) == 'Y') else "N",
                            'itc_availability': 'YES',
                        },
                        'fields': []
                    }
                }
            )

    def _threaded_reconciliation(self, job_id, month, year, tenant_id=None):
        """Background worker for reconciliation."""
        job = GSTJobStatus.objects.get(id=job_id)
        job.status = 'RUNNING'
        job.save()

        try:
            self._run_matching_engine(tenant_id, month, year, job=job)
            job.status = 'COMPLETED'
            job.progress = 100
            job.save()
            
            # Module 5: Trigger Validation after reco
            GSTValidationService.run_period_validation(month, year)

        except Exception as e:
            job.status = 'FAILED'
            job.error_log = str(e)
            job.save()

    @action(detail=False, methods=['post'])
    def run_reconciliation(self, request):
        """Module 3: Matching Engine execution."""
        month = request.data.get('month')
        year = request.data.get('year')
        from core.tenant import get_tenant_from_request
        tenant_id = get_tenant_from_request(request) or getattr(request.user, 'tenant_id', None) or getattr(request.user, 'branch_id', None)
        
        job = GSTJobStatus.objects.create(job_type='RECO', status='PENDING')
        
        # Start background thread
        thread = threading.Thread(target=self._threaded_reconciliation, args=(job.id, month, year, tenant_id))
        thread.start()
        
        return Response({"job_id": job.id, "status": "PENDING"})

    @action(detail=False, methods=['get'])
    def job_status(self, request):
        """Poll job status from frontend."""
        job_id = request.query_params.get('job_id')
        job = GSTJobStatus.objects.get(id=job_id)
        return Response({
            "status": job.status,
            "progress": job.progress,
            "error": job.error_log
        })

    @action(detail=False, methods=['get'])
    def validation_results(self, request):
        """Module 5: Fetch validation warnings."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        results = ValidationResult.objects.filter(period_month=month, period_year=year)
        return Response([{"type": r.check_type, "msg": r.message} for r in results])

    @action(detail=False, methods=['get'])
    def results(self, request):
        """Fetch reconciliation results for GSTR-2B."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        from core.tenant import get_tenant_from_request
        tenant_id = get_tenant_from_request(request) or getattr(request.user, 'tenant_id', None) or getattr(request.user, 'branch_id', None)
        
        try:
            self._run_matching_engine(tenant_id, month, year, job=None)
        except Exception:
            pass
        
        results_qs = ReconciliationResult.objects.select_related('invoice_2b')

        from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
        voucher_ids = [r.purchase_voucher_id for r in results_qs if r.purchase_voucher_id]
        vouchers = VoucherPurchaseSupplierDetails.objects.filter(id__in=voucher_ids)
        voucher_map = {v.id: v for v in vouchers}

        data = []
        for r in results_qs:
            inv = r.invoice_2b
            details = r.matching_details or {}
            
            books_data = details.get('books_data')
            v_ref = voucher_map.get(r.purchase_voucher_id) if r.purchase_voucher_id else None
            if not books_data and v_ref:
                v = v_ref
                line_items = list(v.line_items.all())
                items_val = sum((item.invoice_value or item.taxable_value or (item.rate * item.quantity)) for item in line_items)
                tx_val = sum(item.taxable_value for item in line_items)
                igst_val = sum(item.igst_amount for item in line_items)
                cgst_val = sum(item.cgst_amount for item in line_items)
                sgst_val = sum(item.sgst_amount for item in line_items)
                raw_date = getattr(v, 'supplier_invoice_date', None) or getattr(v, 'date', None)
                books_data = {
                    "purchase_voucher_id": v.id,
                    "invoice_no": getattr(v, 'supplier_invoice_no', '') or getattr(v, 'purchase_voucher_no', ''),
                    "invoice_date": str(raw_date) if raw_date else '',
                    "invoice_value": float(items_val) if items_val else float(getattr(getattr(v, 'due_details', None), 'to_pay', 0) or 0),
                    "taxable_value": float(tx_val),
                    "igst": float(igst_val),
                    "cgst": float(cgst_val),
                    "sgst": float(sgst_val),
                    "vendor_name": getattr(v, 'vendor_name', ''),
                    "supplier_gstin": v.gstin or '',
                    "gstr_period": f"{month} {year}",
                    "reverse_charge": "Y" if (getattr(v, 'input_type', '') == 'RCM' or getattr(v, 'reverse_charge', None) == 'Y') else "N",
                    "itc_availability": details.get('itc_availability', details.get('itc_availment', 'YES')),
                }

            raw_rcm = (inv.raw_data or {}).get('rchrg') or (inv.raw_data or {}).get('rev') or (inv.raw_data or {}).get('reverse_charge') or (inv.raw_data or {}).get('Reverse Charge') or 'N' if inv else (books_data.get('reverse_charge', 'N') if books_data else 'N')
            rcm_str = 'Y' if str(raw_rcm).strip().upper() in ('Y', 'YES', 'TRUE', '1') else 'N'
            inv_fp = (inv.raw_data or {}).get('fp') or (inv.raw_data or {}).get('period') or (inv.raw_data or {}).get('Filing Period') or (inv.raw_data or {}).get('gstr2b_period') or (inv.raw_data or {}).get('return_period') or f"{month} {year}" if inv else (books_data.get('gstr_period', f"{month} {year}") if books_data else f"{month} {year}")

            # Resolve display values
            disp_gstin = inv.gstin if inv else (books_data.get('supplier_gstin') if books_data else (v_ref.gstin if v_ref else ""))
            disp_inv_no = inv.invoice_no if inv else (books_data.get('invoice_no') if books_data else (v_ref.supplier_invoice_no if v_ref else ""))
            disp_inv_date = inv.invoice_date if inv else (books_data.get('invoice_date') if books_data else (str(v_ref.date) if v_ref and v_ref.date else ""))
            disp_inv_val = float(inv.invoice_value) if inv else (float(books_data.get('invoice_value', 0)) if books_data else 0)
            disp_tx_val = float(inv.taxable_value) if inv else (float(books_data.get('taxable_value', 0)) if books_data else 0)
            disp_igst = float(inv.igst) if inv else (float(books_data.get('igst', 0)) if books_data else 0)
            disp_cgst = float(inv.cgst) if inv else (float(books_data.get('cgst', 0)) if books_data else 0)
            disp_sgst = float(inv.sgst) if inv else (float(books_data.get('sgst', 0)) if books_data else 0)
            disp_cess = float(inv.cess) if inv else (float(books_data.get('cess', 0)) if books_data else 0)
            disp_vendor = inv.vendor_name if inv else (books_data.get('vendor_name') if books_data else (v_ref.vendor_name if v_ref else ""))

            data.append({
                "id": r.id,
                "status": r.status,
                "supplier_gstin": disp_gstin,
                "invoice_no": disp_inv_no,
                "invoice_date": str(disp_inv_date),
                "invoice_value": disp_inv_val,
                "taxable_value": disp_tx_val,
                "igst": disp_igst,
                "cgst": disp_cgst,
                "sgst": disp_sgst,
                "cess": disp_cess,
                "reverse_charge": rcm_str,
                "matching_score": r.matching_score,
                "vendor_name": disp_vendor,
                "gstr_period": inv_fp,
                "raw_data": inv.raw_data if inv else {},
                "matching_details": details,
                "mismatches": details.get('mismatches', []),
                "itc_availment": details.get('itc_availment', 'YES'),
                "itc_availability": details.get('itc_availability', details.get('itc_availment', 'YES')),
                "pushed_to_gstr3b": bool(details.get('pushed_to_gstr3b', False)),
                "books_data": books_data
            })
        
        summary = {
            "exact_match": results_qs.filter(status='EXACT').count(),
            "partial_match": results_qs.filter(status='PARTIAL').count(),
            "mismatch": results_qs.filter(status='MISMATCH').count(),
            "missing_in_books": results_qs.filter(status='MISSING_BOOKS').count(),
            "missing_in_2b": results_qs.filter(status='MISSING_2B').count(),
        }
        
        return Response({
            "results": data,
            "summary": summary
        })

    @action(detail=False, methods=['get'])
    def compute_itc(self, request):
        """Module 3: Compute ITC Eligibility (respecting ITC Availment == YES)."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response({"error": "Month and Year are required"}, status=400)
        
        exact_matches = ReconciliationResult.objects.filter(status='EXACT').select_related('invoice_2b')
        total_igst = Decimal('0')
        total_cgst = Decimal('0')
        total_sgst = Decimal('0')
        eligible_igst = Decimal('0')
        eligible_cgst = Decimal('0')
        eligible_sgst = Decimal('0')
        blocked_igst = Decimal('0')

        for r in exact_matches:
            inv = r.invoice_2b
            if not inv:
                continue
            itc_avl_raw = (r.matching_details or {}).get('itc_availment') or (inv.raw_data or {}).get('itcavl') or (inv.raw_data or {}).get('itc_avl') or (inv.raw_data or {}).get('itc_availment') or (inv.raw_data or {}).get('ITC Eligible') or 'Y'
            is_itc_avail = str(itc_avl_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1')

            total_igst += inv.igst
            total_cgst += inv.cgst
            total_sgst += inv.sgst

            if is_itc_avail:
                eligible_igst += inv.igst
                eligible_cgst += inv.cgst
                eligible_sgst += inv.sgst
            else:
                blocked_igst += (inv.igst + inv.cgst + inv.sgst)

        itc = ITCSummary.objects.create(
            period_month=month, period_year=year,
            total_itc_igst=total_igst,
            total_itc_cgst=total_cgst,
            total_itc_sgst=total_sgst,
            eligible_itc_igst=eligible_igst,
            eligible_itc_cgst=eligible_cgst,
            eligible_itc_sgst=eligible_sgst,
            blocked_itc_igst=blocked_igst,
        )
        return Response(ITCSummarySerializer(itc).data)

    @action(detail=False, methods=['get'])
    def gstr3b_preview(self, request):
        """Module 4: GSTR-3B Computation."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        tenant_id = getattr(request.user, 'tenant_id', None)

        # Liability (READ ONLY)
        if tenant_id:
            sales = VoucherSalesInvoiceDetails.objects.filter(tenant_id=tenant_id)
        else:
            sales = VoucherSalesInvoiceDetails.objects.all()
        output_tax = {'igst': 0, 'cgst': 0, 'sgst': 0}
        for v in sales:
            pay = getattr(v, 'payment_details', None)
            if pay:
                output_tax['igst'] += float(pay.payment_igst)
                output_tax['cgst'] += float(pay.payment_cgst)
                output_tax['sgst'] += float(pay.payment_sgst)

        # Auto-Compute ITC on the fly from EXACT matches where ITC Availment == YES
        exact_matches = ReconciliationResult.objects.filter(status='EXACT').select_related('invoice_2b')
        input_igst = Decimal('0')
        input_cgst = Decimal('0')
        input_sgst = Decimal('0')

        for r in exact_matches:
            inv = r.invoice_2b
            if not inv:
                continue
            itc_avl_raw = (r.matching_details or {}).get('itc_availment') or (inv.raw_data or {}).get('itcavl') or (inv.raw_data or {}).get('itc_avl') or (inv.raw_data or {}).get('itc_availment') or (inv.raw_data or {}).get('ITC Eligible') or 'Y'
            is_itc_avail = str(itc_avl_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1')

            if is_itc_avail:
                input_igst += inv.igst
                input_cgst += inv.cgst
                input_sgst += inv.sgst

        input_tax = {
            'igst': float(input_igst),
            'cgst': float(input_cgst),
            'sgst': float(input_sgst),
        }
        
        # Bulletproof lookup: prefer FILED record, then latest DRAFT, then create new
        qs = GSTR3BReport.objects.filter(period_month=month, period_year=year)
        filed = qs.filter(status='FILED').order_by('-created_at').first()
        
        if filed:
            report = filed
        else:
            report = qs.order_by('-created_at').first()
            if not report:
                report = GSTR3BReport.objects.create(
                    period_month=month,
                    period_year=year
                )

        # Only update the numbers if it's still in DRAFT mode
        if report.status != 'FILED':
            report.output_tax_igst = output_tax['igst']
            report.output_tax_cgst = output_tax['cgst']
            report.output_tax_sgst = output_tax['sgst']
            
            report.input_tax_igst = input_tax['igst']
            report.input_tax_cgst = input_tax['cgst']
            report.input_tax_sgst = input_tax['sgst']
            
            report.net_igst = max(0, output_tax['igst'] - input_tax['igst'])
            report.net_cgst = max(0, output_tax['cgst'] - input_tax['cgst'])
            report.net_sgst = max(0, output_tax['sgst'] - input_tax['sgst'])
            
            report.save()

        data = GSTR3BReportSerializer(report).data
        data['status'] = report.status
        data['arn_number'] = report.arn_number
        data['filed_date'] = report.filed_date
        return Response(data)

    @action(detail=False, methods=['post'])
    def push_to_gstr3b(self, request):
        """
        Module 4: Bulk Push EXACT MATCH reconciliation records into GSTR-3B Summary.
        Only records with status == 'EXACT' are eligible.
        Records with ITC Availment == 'YES' contribute to eligible ITC.
        Records with ITC Availment == 'NO' are marked pushed but excluded from eligible ITC.
        """
        month = request.data.get('month')
        year = request.data.get('year')
        reconciliation_ids = request.data.get('reconciliation_ids', [])

        if not month or not year:
            return Response({"error": "Month and Year are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not reconciliation_ids or not isinstance(reconciliation_ids, list):
            return Response({"error": "At least one reconciliation record must be selected."}, status=status.HTTP_400_BAD_REQUEST)

        from core.tenant import get_tenant_from_request
        tenant_id = get_tenant_from_request(request) or getattr(request.user, 'tenant_id', None) or getattr(request.user, 'branch_id', None)

        # 1. Fetch records and validate existence
        qs = ReconciliationResult.objects.filter(id__in=reconciliation_ids).select_related('invoice_2b')
        if qs.count() != len(reconciliation_ids):
            return Response(
                {"error": "One or more selected reconciliation records could not be found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Strict Period, Tenant & EXACT MATCH validation for every record
        reco_period = self._normalize_reco_period(month, year)
        
        for r in qs:
            # Tenant isolation
            if tenant_id and getattr(r, 'tenant_id', None) and r.tenant_id != tenant_id:
                return Response(
                    {"error": f"Reconciliation record #{r.id} belongs to a different tenant/branch."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Strict EXACT MATCH validation
            if r.status != 'EXACT':
                return Response(
                    {"error": f"Cannot push records because invoice '{r.invoice_2b.invoice_no if r.invoice_2b else r.id}' has status '{r.status}'. Only EXACT MATCH records can be pushed to GSTR-3B."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Period validation
            if r.invoice_2b and reco_period:
                raw_fp = (r.invoice_2b.raw_data or {}).get('fp') or (r.invoice_2b.raw_data or {}).get('Filing Period')
                norm_fp = self._normalize_period(raw_fp)
                if norm_fp and norm_fp != reco_period:
                    return Response(
                        {"error": f"Invoice '{r.invoice_2b.invoice_no}' belongs to return period {raw_fp}, which does not match current period {month} {year}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 3. Atomic Transaction for Push & Aggregation
        from django.db import transaction
        from django.utils import timezone

        pushed_count = 0
        pushed_igst = Decimal('0')
        pushed_cgst = Decimal('0')
        pushed_sgst = Decimal('0')
        pushed_cess = Decimal('0')

        with transaction.atomic():
            now_iso = timezone.now().isoformat()
            for r in qs:
                details = r.matching_details or {}
                details['pushed_to_gstr3b'] = True
                details['pushed_at'] = now_iso
                r.matching_details = details
                r.save(update_fields=['matching_details'])
                pushed_count += 1

            # Aggregate all pushed EXACT records for this period (preventing double counting)
            all_exact_recos = ReconciliationResult.objects.filter(status='EXACT').select_related('invoice_2b')
            
            agg_igst = Decimal('0')
            agg_cgst = Decimal('0')
            agg_sgst = Decimal('0')
            agg_cess = Decimal('0')

            for rec in all_exact_recos:
                rec_details = rec.matching_details or {}
                if rec_details.get('pushed_to_gstr3b'):
                    inv = rec.invoice_2b
                    if not inv:
                        continue
                    
                    if reco_period:
                        raw_fp = (inv.raw_data or {}).get('fp') or (inv.raw_data or {}).get('Filing Period')
                        norm_fp = self._normalize_period(raw_fp)
                        if norm_fp and norm_fp != reco_period:
                            continue

                    itc_avl_raw = rec_details.get('itc_availability') or rec_details.get('itc_availment') or (inv.raw_data or {}).get('itcavl') or (inv.raw_data or {}).get('ITC Eligible') or 'Y'
                    is_itc_avail = str(itc_avl_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1')

                    if is_itc_avail:
                        agg_igst += inv.igst
                        agg_cgst += inv.cgst
                        agg_sgst += inv.sgst
                        agg_cess += inv.cess

            # Delta of newly pushed records for summary response
            for r in qs:
                inv = r.invoice_2b
                if inv:
                    itc_avl_raw = (r.matching_details or {}).get('itc_availability') or (r.matching_details or {}).get('itc_availment') or (inv.raw_data or {}).get('itcavl') or (inv.raw_data or {}).get('ITC Eligible') or 'Y'
                    if str(itc_avl_raw).strip().upper() in ('Y', 'YES', 'TRUE', '1'):
                        pushed_igst += inv.igst
                        pushed_cgst += inv.cgst
                        pushed_sgst += inv.sgst
                        pushed_cess += inv.cess

            # Update GSTR-3B Report (if not filed)
            report, _ = GSTR3BReport.objects.get_or_create(
                period_month=month,
                period_year=year
            )

            if report.status != 'FILED':
                if tenant_id:
                    sales = VoucherSalesInvoiceDetails.objects.filter(tenant_id=tenant_id)
                else:
                    sales = VoucherSalesInvoiceDetails.objects.all()
                out_igst = Decimal('0')
                out_cgst = Decimal('0')
                out_sgst = Decimal('0')
                for v in sales:
                    pay = getattr(v, 'payment_details', None)
                    if pay:
                        out_igst += Decimal(str(pay.payment_igst or 0))
                        out_cgst += Decimal(str(pay.payment_cgst or 0))
                        out_sgst += Decimal(str(pay.payment_sgst or 0))

                report.output_tax_igst = out_igst
                report.output_tax_cgst = out_cgst
                report.output_tax_sgst = out_sgst

                report.input_tax_igst = agg_igst
                report.input_tax_cgst = agg_cgst
                report.input_tax_sgst = agg_sgst

                report.net_igst = max(Decimal('0'), out_igst - agg_igst)
                report.net_cgst = max(Decimal('0'), out_cgst - agg_cgst)
                report.net_sgst = max(Decimal('0'), out_sgst - agg_sgst)
                report.save()

            # Update / Create ITCSummary
            ITCSummary.objects.update_or_create(
                period_month=month,
                period_year=year,
                defaults={
                    'total_itc_igst': agg_igst,
                    'total_itc_cgst': agg_cgst,
                    'total_itc_sgst': agg_sgst,
                    'eligible_itc_igst': agg_igst,
                    'eligible_itc_cgst': agg_cgst,
                    'eligible_itc_sgst': agg_sgst,
                    'blocked_itc_igst': Decimal('0'),
                }
            )

        return Response({
            "success": True,
            "message": f"{pushed_count} invoices successfully pushed to GSTR-3B.",
            "pushed_count": pushed_count,
            "totals": {
                "igst": float(pushed_igst),
                "cgst": float(pushed_cgst),
                "sgst": float(pushed_sgst),
                "cess": float(pushed_cess),
                "total_itc": float(pushed_igst + pushed_cgst + pushed_sgst + pushed_cess)
            },
            "gstr3b_summary": {
                "input_tax_igst": float(agg_igst),
                "input_tax_cgst": float(agg_cgst),
                "input_tax_sgst": float(agg_sgst),
                "total_input_tax": float(agg_igst + agg_cgst + agg_sgst)
            }
        })

    @action(detail=False, methods=['delete'])
    def clear_data(self, request):
        """Action to remove all experimental/seed data in higher isolation."""
        GSTR2BInvoice.objects.all().delete()
        ReconciliationResult.objects.all().delete()
        ITCSummary.objects.all().delete()
        GSTR3BReport.objects.all().delete()
        ValidationResult.objects.all().delete()
        GSTJobStatus.objects.all().delete()
        AuditLog.objects.create(
            action="Data Purge",
            details={"message": "All reconciliation data cleared by user request"},
            executed_by=str(request.user)
        )
        return Response({"status": "All module data cleared successfully"})

    @action(detail=False, methods=['post'])
    def file_gstr1_sandbox(self, request):
        """Module: Direct Filing via Sandbox API (Mocked)"""
        month = request.data.get('month')
        year = request.data.get('year')
        
        service = SandboxGSTService()
        result = service.file_gstr1(month, year, request.data)
        
        AuditLog.objects.create(
            action="Sandbox GSTR-1 File (Mock)",
            details={"month": month, "year": year, "reference": result.get("reference_id")},
            executed_by=str(request.user) if request.user.is_authenticated else 'system'
        )
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['get'])
    def fetch_gstr2b_sandbox(self, request):
        """Module: Direct Fetch via Sandbox API (Mocked)"""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        gstin = request.query_params.get('gstin', '27AAPCU4669C1Z9')
        
        service = SandboxGSTService()
        result = service.fetch_gstr2b(gstin, month, year)
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['post'])
    def request_sandbox_otp(self, request):
        gstin = request.data.get('gstin', '29AAACQ3770E000')
        service = SandboxGSTService()
        result = service.request_otp(gstin)
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['post'])
    def verify_and_file_sandbox(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        gstin = request.data.get('gstin', '29AAACQ3770E000')
        otp = request.data.get('otp')
        
        service = SandboxGSTService()
        verify_result = service.verify_otp(gstin, otp)
        
        if not verify_result.get('success'):
            return Response(verify_result, status=status.HTTP_400_BAD_REQUEST)
            
        auth_token = verify_result.get('auth_token')
        file_result = service.file_gstr1(month, year, request.data, auth_token=auth_token)
        
        AuditLog.objects.create(
            action="Sandbox GSTR-1 File with OTP",
            details={"month": month, "year": year, "reference": file_result.get("reference_id")},
            executed_by=str(request.user) if request.user.is_authenticated else 'system'
        )
        
        if not file_result.get('success'):
            return Response(file_result, status=status.HTTP_400_BAD_REQUEST)

        # Successfully filed! Now mark all vouchers for this month as filed in our database
        months_map = {
            'January': (1, 1), 'February': (2, 1), 'March': (3, 1),
            'April': (4, 0), 'May': (5, 0), 'June': (6, 0),
            'July': (7, 0), 'August': (8, 0), 'September': (9, 0),
            'October': (10, 0), 'November': (11, 0), 'December': (12, 0)
        }
        month_info = months_map.get(month)
        if month_info and year:
            start_year = int(year.split('-')[0])
            filter_year = start_year + month_info[1]
            from accounting.models_voucher_sales import VoucherSalesInvoiceDetails
            from accounting.models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
            
            sales_qs = VoucherSalesInvoiceDetails.objects.filter(
                date__year=filter_year,
                date__month=month_info[0],
                gst_registered=''
            )
            sales_count = sales_qs.update(gst_registered='Yes')
            
            cn_qs = VoucherCreditNoteInvoiceDetails.objects.filter(
                date__year=filter_year,
                date__month=month_info[0],
                gst_registered=''
            )
            cn_count = cn_qs.update(gst_registered='Yes')
            
            from accounting.models import AdvanceAllocation
            adv_qs = AdvanceAllocation.objects.filter(
                transaction__date__year=filter_year,
                transaction__date__month=month_info[0],
                transaction__transaction_type='RECEIPT',
                gst_registered=''
            )
            adv_count = adv_qs.update(gst_registered='Yes')
            
            file_result['message'] += f" (Updated {sales_count} sales vouchers, {cn_count} credit notes, and {adv_count} advances in database)"

        return Response(file_result)

    @action(detail=False, methods=['get'])
    def fetch_ledger_balances(self, request):
        from .models import GSTElectronicLedger
        ledger, _ = GSTElectronicLedger.objects.get_or_create(id=1)
        # Give some initial fake cash so they don't have to pay everything if they don't want to
        if ledger.cash_balance == 0:
            ledger.cash_balance = 50000.00
            ledger.save()
            
        return Response({
            'cash_balance': float(ledger.cash_balance),
            'credit_balance_igst': float(ledger.credit_balance_igst),
            'credit_balance_cgst': float(ledger.credit_balance_cgst),
            'credit_balance_sgst': float(ledger.credit_balance_sgst),
            'liability_balance': float(ledger.liability_balance)
        })

    @action(detail=False, methods=['post'])
    def generate_pmt06_challan(self, request):
        amount = request.data.get('amount', 0)
        
        from .models import GSTElectronicLedger
        ledger, _ = GSTElectronicLedger.objects.get_or_create(id=1)
        
        # Simulate a successful bank deposit by instantly adding to the wallet
        ledger.cash_balance = float(ledger.cash_balance) + float(amount)
        ledger.save()
        
        return Response({
            'success': True,
            'message': f'Challan for ₹{amount} generated and paid successfully! CPIN: 23072600012345',
            'new_balance': float(ledger.cash_balance)
        })

    @action(detail=False, methods=['post'])
    def file_gstr3b_sandbox(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        otp = request.data.get('otp')
        gstin = request.data.get('gstin', '29AAACQ3770E000')
        paid_via_cash = request.data.get('paid_via_cash', 0)

        if not month or not year or not otp:
            return Response({'success': False, 'message': 'Missing required fields'})

        from .models import GSTElectronicLedger, GSTR3BReport
        import uuid
        from django.utils import timezone
        
        # 1. Duplicate Prevention Check
        report, created = GSTR3BReport.objects.get_or_create(
            period_month=month,
            period_year=year
        )

        if report.status == 'FILED':
            return Response({
                'success': False,
                'message': f'Return for {month} {year} is already filed with ARN {report.arn_number}'
            })

        # 2. Verify OTP via Sandbox
        service = SandboxGSTService()
        verify_result = service.verify_otp(gstin, otp)
        
        if not verify_result.get('success'):
            return Response(verify_result, status=status.HTTP_400_BAD_REQUEST)
            
        auth_token = verify_result.get('auth_token')
        
        # 3. Submit Filing via Sandbox
        file_result = service.file_gstr3b(month, year, request.data, auth_token=auth_token)
        if not file_result.get('success'):
            return Response(file_result, status=status.HTTP_400_BAD_REQUEST)

        # 4. Deduct Cash Ledger if needed
        ledger, _ = GSTElectronicLedger.objects.get_or_create(id=1)
        if ledger:
            ledger.cash_balance = float(ledger.cash_balance) - float(paid_via_cash)
            if ledger.cash_balance < 0:
                ledger.cash_balance = 0
            ledger.save()

        # Mark as FILED locally
        report.status = 'FILED'
        report.arn_number = file_result.get('arn', f"AA2907{str(uuid.uuid4().int)[:8]}")
        report.filed_date = timezone.now()
        report.save()
        
        AuditLog.objects.create(
            action="Sandbox GSTR-3B File with OTP",
            details={"month": month, "year": year, "reference": file_result.get("reference_id")},
            executed_by=str(request.user) if request.user.is_authenticated else 'system'
        )

        return Response({
            'success': True,
            'message': file_result.get('message', f'GSTR-3B for {month} {year} successfully filed!'),
            'arn': report.arn_number
        })

    @action(detail=False, methods=['get'])
    def calculate_late_fees(self, request):
        """Part 2: Late Fee Penalty Engine. Scans all periods and computes penalties."""
        from datetime import date

        MONTHS_ORDER = [
            'April', 'May', 'June', 'July', 'August', 'September',
            'October', 'November', 'December', 'January', 'February', 'March'
        ]
        MONTH_NUMBER = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        # Due date = 20th of the NEXT calendar month
        NEXT_MONTH = {
            'January': (2, 0), 'February': (3, 0), 'March': (4, 0),
            'April': (5, 0), 'May': (6, 0), 'June': (7, 0),
            'July': (8, 0), 'August': (9, 0), 'September': (10, 0),
            'October': (11, 0), 'November': (12, 0), 'December': (1, 1)
        }

        year_str = request.query_params.get('year', '2024-25')
        start_year = int(year_str.split('-')[0])
        today = date.today()
        results = []

        # Fetch penalty factors from Sandbox API
        service = SandboxGSTService()
        fee_data = service.fetch_late_fees(year_str)
        factors = fee_data.get('data', {})
        rate_nil = factors.get('daily_rate_nil_return', 10)
        rate_std = factors.get('daily_rate_standard', 25)
        max_nil = factors.get('max_penalty_nil', 250)
        max_std = factors.get('max_penalty_standard', 5000)

        # Only process months that have a real GSTR3BReport record in the database
        real_reports = GSTR3BReport.objects.filter(period_year=year_str).order_by('created_at')
        # De-duplicate: for each month, prefer FILED over DRAFT
        seen_months = {}
        for r in real_reports:
            m = r.period_month
            if m not in seen_months or r.status == 'FILED':
                seen_months[m] = r

        for month_name, report_obj in seen_months.items():
            month_num = MONTH_NUMBER[month_name]
            # Determine calendar year for this period
            cal_year = start_year if month_num >= 4 else start_year + 1

            next_month_num, year_offset = NEXT_MONTH[month_name]
            due_date = date(cal_year + year_offset, next_month_num, 20)

            # Use the real report from database
            filed_report = report_obj if report_obj.status == 'FILED' else None
            filed_date = filed_report.filed_date.date() if filed_report and filed_report.filed_date else None

            # Calculate days late
            comparison_date = filed_date if filed_date else today
            days_late = max(0, (comparison_date - due_date).days)

            # Determine if NIL return (all net taxes are zero)
            is_nil = False
            if filed_report:
                is_nil = (
                    float(filed_report.net_igst or 0) == 0 and
                    float(filed_report.net_cgst or 0) == 0 and
                    float(filed_report.net_sgst or 0) == 0
                )

            # Calculate fee per GST rules using Sandbox configuration
            if days_late > 0:
                daily_rate = rate_nil if is_nil else rate_std
                cgst_fee = days_late * daily_rate
                sgst_fee = days_late * daily_rate
                
                max_cap = max_nil if is_nil else max_std
                cgst_fee = min(cgst_fee, max_cap)
                sgst_fee = min(sgst_fee, max_cap)
                
                total_fee = cgst_fee + sgst_fee
            else:
                cgst_fee = sgst_fee = total_fee = 0

            # Upsert GSTLateFee record if there is a penalty
            if days_late > 0:
                late_fee_obj, _ = GSTLateFee.objects.get_or_create(
                    return_type='GSTR3B',
                    period_month=month_name,
                    period_year=year_str,
                    defaults={'due_date': due_date}
                )
                if late_fee_obj.status == 'PENDING':
                    late_fee_obj.due_date = due_date
                    late_fee_obj.filed_date = filed_date
                    late_fee_obj.days_late = days_late
                    late_fee_obj.is_nil_return = is_nil
                    late_fee_obj.cgst_late_fee = cgst_fee
                    late_fee_obj.sgst_late_fee = sgst_fee
                    late_fee_obj.total_late_fee = total_fee
                    late_fee_obj.save()
                fee_status = late_fee_obj.status
                late_fee_id = late_fee_obj.id
            else:
                fee_status = 'ON_TIME'
                late_fee_id = None

            results.append({
                'period_month': month_name,
                'period_year': year_str,
                'due_date': due_date.isoformat(),
                'filed_date': filed_date.isoformat() if filed_date else None,
                'is_filed': filed_date is not None,
                'days_late': days_late,
                'is_nil_return': is_nil,
                'cgst_late_fee': cgst_fee,
                'sgst_late_fee': sgst_fee,
                'total_late_fee': total_fee,
                'status': fee_status,
                'late_fee_id': late_fee_id,
                'arn_number': filed_report.arn_number if filed_report else None,
            })

        return Response({'results': results, 'year': year_str})

    @action(detail=False, methods=['post'])
    def pay_late_fee(self, request):
        """Pay a pending late fee from the Electronic Cash Ledger."""
        late_fee_id = request.data.get('late_fee_id')
        if not late_fee_id:
            return Response({'error': 'late_fee_id is required'}, status=400)

        try:
            late_fee = GSTLateFee.objects.get(id=late_fee_id)
        except GSTLateFee.DoesNotExist:
            return Response({'error': 'Late fee record not found'}, status=404)

        if late_fee.status == 'PAID':
            return Response({'error': 'This late fee has already been paid'}, status=400)

        amount = late_fee.total_late_fee
        ledger, _ = GSTElectronicLedger.objects.get_or_create(id=1)

        # Sandbox: auto-top-up if needed
        if ledger.cash_balance < amount:
            ledger.cash_balance += amount

        ledger.cash_balance -= amount
        ledger.save()

        from django.utils import timezone
        late_fee.status = 'PAID'
        late_fee.paid_date = timezone.now()
        late_fee.save()

        AuditLog.objects.create(
            action="Late Fee Payment",
            details={
                'period': f"{late_fee.period_month} {late_fee.period_year}",
                'amount_paid': float(amount)
            },
            executed_by=str(request.user) if request.user.is_authenticated else 'system'
        )

        return Response({
            'success': True,
            'message': f'Late fee of ₹{amount} paid successfully for {late_fee.period_month} {late_fee.period_year}',
            'amount_paid': float(amount)
        })
