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
        """Module 1: Ingest GSTR-2B JSON data."""
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of invoices"}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        duplicate_count = 0

        for inv in data:
            try:
                gstin = str(inv.get('gstin', '')).strip().upper()
                inv_no = str(inv.get('invoice_no', '')).strip()
                inv_date = inv.get('invoice_date')
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
                    raw_data=inv
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

    def _threaded_reconciliation(self, job_id, month, year, tenant_id=None):
        """Background worker for reconciliation."""
        job = GSTJobStatus.objects.get(id=job_id)
        job.status = 'RUNNING'
        job.save()

        try:
            invoices_2b = GSTR2BInvoice.objects.all() # In production: filter by date
            if tenant_id:
                vouchers_books = VoucherPurchaseSupplierDetails.objects.filter(tenant_id=tenant_id)
            else:
                vouchers_books = VoucherPurchaseSupplierDetails.objects.all()
            total = invoices_2b.count()
            
            for index, inv_2b in enumerate(invoices_2b):
                matches = vouchers_books.filter(gstin=inv_2b.gstin)
                best_match = None
                max_score = 0
                
                for v in matches:
                    score = 0
                    if v.supplier_invoice_no.strip().lower() == inv_2b.invoice_no.strip().lower():
                        score += 50
                    
                    # Fuzzy date check (±3 days)
                    if abs((v.date - inv_2b.invoice_date).days) <= 3:
                        score += 20
                        
                    # Fuzzy value check (±2%)
                    v_val = sum(item.invoice_value for item in v.line_items.all())
                    if v_val and inv_2b.invoice_value:
                        diff_pct = abs(float(v_val) - float(inv_2b.invoice_value)) / float(inv_2b.invoice_value)
                        if diff_pct <= 0.02:
                            score += 30
                    elif v_val == 0 and inv_2b.invoice_value == 0:
                        score += 30

                    if score > max_score:
                        max_score = score
                        best_match = v

                status_label = 'MISMATCH'
                if max_score >= 70: status_label = 'EXACT'
                elif max_score >= 50: status_label = 'PARTIAL'
                
                ReconciliationResult.objects.update_or_create(
                    invoice_2b=inv_2b,
                    defaults={
                        'purchase_voucher_id': best_match.id if best_match else None,
                        'matching_score': max_score,
                        'status': status_label if best_match else 'MISSING_BOOKS'
                    }
                )
                
                if index % 10 == 0:
                    job.progress = int((index / total) * 100)
                    job.save()

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
        tenant_id = getattr(request.user, 'tenant_id', None)
        
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
        
        results_qs = ReconciliationResult.objects.select_related('invoice_2b')
        if month and year:
            # We filter by the uploaded 2B invoice date loosely based on the month/year selected
            # Since mock data will just use the current month/year, we can filter by exact matching or just return all for sandbox
            # For this simple prototype, let's just return all and we will clear them out per fetch
            pass

        from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
        voucher_ids = [r.purchase_voucher_id for r in results_qs if r.purchase_voucher_id]
        vouchers = VoucherPurchaseSupplierDetails.objects.filter(id__in=voucher_ids)
        voucher_map = {v.id: v for v in vouchers}

        data = []
        for r in results_qs:
            inv = r.invoice_2b
            
            books_data = None
            if r.purchase_voucher_id and r.purchase_voucher_id in voucher_map:
                v = voucher_map[r.purchase_voucher_id]
                items_val = sum(item.invoice_value for item in v.line_items.all())
                books_data = {
                    "purchase_voucher_id": v.id,
                    "invoice_no": getattr(v, 'supplier_invoice_no', ''),
                    "invoice_date": getattr(v, 'date', None),
                    "invoice_value": float(items_val),
                    "vendor_name": getattr(v, 'vendor_name', ''),
                }

            data.append({
                "id": r.id,
                "status": r.status,
                "supplier_gstin": inv.gstin if inv else "",
                "invoice_no": inv.invoice_no if inv else "",
                "invoice_date": inv.invoice_date if inv else "",
                "invoice_value": inv.invoice_value if inv else 0,
                "matching_score": r.matching_score,
                "vendor_name": inv.vendor_name if inv else "",
                "books_data": books_data
            })
        
        summary = {
            "exact_match": results_qs.filter(status='EXACT').count(),
            "partial_match": results_qs.filter(status='PARTIAL').count(),
            "missing_in_books": results_qs.filter(status='MISSING_BOOKS').count(),
            "missing_in_2b": results_qs.filter(status='MISSING_2B').count(),
        }
        
        return Response({
            "results": data,
            "summary": summary
        })

    @action(detail=False, methods=['get'])
    def compute_itc(self, request):
        """Module 3: Compute ITC Eligibility."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response({"error": "Month and Year are required"}, status=400)
        
        exact_matches = ReconciliationResult.objects.filter(status='EXACT')
        summary = exact_matches.aggregate(
            igst=Sum('invoice_2b__igst'),
            cgst=Sum('invoice_2b__cgst'),
            sgst=Sum('invoice_2b__sgst'),
        )

        itc = ITCSummary.objects.create(
            period_month=month, period_year=year,
            total_itc_igst=summary['igst'] or 0,
            total_itc_cgst=summary['cgst'] or 0,
            total_itc_sgst=summary['sgst'] or 0,
            eligible_itc_igst=summary['igst'] or 0,
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

        # Auto-Compute ITC on the fly from EXACT matches
        from django.db.models import Sum
        exact_matches = ReconciliationResult.objects.filter(status='EXACT')
        summary = exact_matches.aggregate(
            igst=Sum('invoice_2b__igst'),
            cgst=Sum('invoice_2b__cgst'),
            sgst=Sum('invoice_2b__sgst'),
        )
        input_tax = {
            'igst': float(summary['igst'] or 0),
            'cgst': float(summary['cgst'] or 0),
            'sgst': float(summary['sgst'] or 0),
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
        gstin = request.data.get('gstin', '29ABCDE1234F1Z5')
        service = SandboxGSTService()
        result = service.request_otp(gstin)
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['post'])
    def verify_and_file_sandbox(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        gstin = request.data.get('gstin', '29ABCDE1234F1Z5')
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
        paid_via_cash = request.data.get('paid_via_cash', 0)
        
        if not month or not year or not otp:
            return Response({'success': False, 'message': 'Missing required fields'})
            
        from .models import GSTElectronicLedger, GSTR3BReport
        
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
            
        ledger, _ = GSTElectronicLedger.objects.get_or_create(id=1)
        if ledger:
            # Deduct the cash they used to pay this liability
            ledger.cash_balance = float(ledger.cash_balance) - float(paid_via_cash)
            if ledger.cash_balance < 0:
                ledger.cash_balance = 0
            ledger.save()
            
        import uuid
        from django.utils import timezone
        arn = f"AA2907{str(uuid.uuid4().int)[:8]}"
        
        # Mark as FILED
        report.status = 'FILED'
        report.arn_number = arn
        report.filed_date = timezone.now()
        report.save()
            
        return Response({
            'success': True,
            'message': f'GSTR-3B for {month} {year} successfully filed! ARN: {arn}',
            'arn': arn
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

            # Calculate fee per GST rules
            if days_late > 0:
                daily_rate = 10 if is_nil else 25  # per component (CGST + SGST)
                cgst_fee = days_late * daily_rate
                sgst_fee = days_late * daily_rate
                if is_nil:
                    cgst_fee = min(cgst_fee, 250)
                    sgst_fee = min(sgst_fee, 250)
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
