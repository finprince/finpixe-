import pandas as pd
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
# REMOVED: HasSubmoduleAccess - no longer using permission tables
from rest_framework.response import Response
from django.db.models import Q
# TODO: Update reports to query new split tables
# from accounting.models import Voucher, Ledger
# from inventory.models import StockItem
from .mixins import IsBranchMember
import io
import os
import json
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Configure AI Provider
from .ai_proxy import api_key_manager

class BaseExcelView(APIView):
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get_filtered_vouchers(self, request):
        """Fetch vouchers from all split tables and combine them"""
        from accounting.models_voucher_sales import VoucherSalesInvoiceDetails as VoucherSales
        from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails as VoucherPurchase
        from accounting.models import Transaction  # Payment and Receipt both use Transaction model
        from accounting.models_voucher_contra import VoucherContra
        from accounting.models_voucher_journal import VoucherJournal
        from accounting.models import Voucher as GenericVoucher
        VoucherPayment = Transaction
        VoucherReceipt = Transaction
        
        tenant_id = request.tenant_id
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        vouchers = []
        
        # Fetch Sales vouchers
        sales_qs = VoucherSales.objects.filter(tenant_id=tenant_id)
        if start_date:
            sales_qs = sales_qs.filter(date__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(date__lte=end_date)
        payment_details_prefetch = {}
        try:
            from accounting.models_voucher_sales import VoucherSalesPaymentDetails
            for pd in VoucherSalesPaymentDetails.objects.filter(invoice__in=sales_qs).select_related('invoice'):
                payment_details_prefetch[pd.invoice_id] = pd
        except Exception:
            pass
        for v in sales_qs:
            pd = payment_details_prefetch.get(v.id)
            total_val = float(pd.payment_invoice_value if pd else 0) or float(getattr(v, 'total', 0) or 0)
            vouchers.append({
                'date': v.date,
                'type': 'Sales',
                'voucher_number': v.sales_invoice_no,
                'invoice_no': v.sales_invoice_no,
                'party': v.customer_name,
                'account': '',
                'total': total_val,
                'amount': total_val,
                'narration': getattr(v, 'narration', '') or '',
                'id': v.id,
            })
        
        # Fetch Purchase vouchers
        purchase_qs = VoucherPurchase.objects.filter(tenant_id=tenant_id)
        if start_date:
            purchase_qs = purchase_qs.filter(date__gte=start_date)
        if end_date:
            purchase_qs = purchase_qs.filter(date__lte=end_date)
        for v in purchase_qs:
            # Get total from related supply details (INR or foreign)
            inr_total = 0.0
            try:
                inr = v.supply_inr_details.first()
                inr_total = float(inr.invoice_total if inr else 0)
            except Exception:
                pass
            vouchers.append({
                'date': v.date,
                'type': 'Purchase',
                'voucher_number': v.purchase_voucher_no or v.supplier_invoice_no,
                'invoice_no': v.supplier_invoice_no,
                'party': v.vendor_name,
                'account': '',
                'total': inr_total,
                'amount': inr_total,
                'narration': '',
                'id': v.id,
            })
        
        # Fetch Payment vouchers (Transaction model, transaction_type=PAYMENT)
        payment_qs = VoucherPayment.objects.filter(tenant_id=tenant_id, transaction_type='PAYMENT')
        if start_date:
            payment_qs = payment_qs.filter(date__gte=start_date)
        if end_date:
            payment_qs = payment_qs.filter(date__lte=end_date)
        for v in payment_qs:
            party_name = v.pay_to_ledger.name if v.pay_to_ledger else ''
            account_name = v.pay_from_ledger.name if v.pay_from_ledger else ''
            vouchers.append({
                'date': v.date,
                'type': 'Payment',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': party_name,
                'account': account_name,
                'total': 0,
                'amount': float(v.amount),
                'narration': v.narration or '',
                'id': v.id,
            })
        
        # Fetch Receipt vouchers (Transaction model, transaction_type=RECEIPT)
        receipt_qs = VoucherReceipt.objects.filter(tenant_id=tenant_id, transaction_type='RECEIPT')
        if start_date:
            receipt_qs = receipt_qs.filter(date__gte=start_date)
        if end_date:
            receipt_qs = receipt_qs.filter(date__lte=end_date)
        for v in receipt_qs:
            party_name = v.pay_from_ledger.name if v.pay_from_ledger else ''
            account_name = v.pay_to_ledger.name if v.pay_to_ledger else ''
            vouchers.append({
                'date': v.date,
                'type': 'Receipt',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': party_name,
                'account': account_name,
                'total': 0,
                'amount': float(v.amount),
                'narration': v.narration or '',
                'id': v.id,
            })
        
        # Fetch Contra vouchers
        contra_qs = VoucherContra.objects.filter(tenant_id=tenant_id)
        if start_date:
            contra_qs = contra_qs.filter(date__gte=start_date)
        if end_date:
            contra_qs = contra_qs.filter(date__lte=end_date)
        for v in contra_qs:
            vouchers.append({
                'date': v.date,
                'type': 'Contra',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': v.from_account,
                'account': v.to_account,
                'total': 0,
                'amount': float(v.amount),
                'narration': v.narration or '',
                'id': v.id,
            })
        
        # Fetch Journal vouchers
        journal_qs = VoucherJournal.objects.filter(tenant_id=tenant_id)
        if start_date:
            journal_qs = journal_qs.filter(date__gte=start_date)
        if end_date:
            journal_qs = journal_qs.filter(date__lte=end_date)
        for v in journal_qs:
            vouchers.append({
                'date': v.date,
                'type': 'Journal',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': '',
                'account': '',
                'total': float(v.total_debit),
                'amount': float(v.total_debit),
                'narration': v.narration or '',
                'id': v.id,
            })

        # Fetch Debit Note vouchers from the generic Voucher table
        # (type='debit_note', party=vendor_name, total=net_amount_due)
        dnote_qs = GenericVoucher.objects.filter(tenant_id=tenant_id, type='debit_note')
        if start_date:
            dnote_qs = dnote_qs.filter(date__gte=start_date)
        if end_date:
            dnote_qs = dnote_qs.filter(date__lte=end_date)
        for v in dnote_qs:
            vouchers.append({
                'date': v.date,
                'type': 'Debit Note',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': v.party or '',
                'account': '',
                'total': float(v.total or 0),
                'amount': float(v.total or 0),
                'narration': v.narration or '',
                'id': v.id,
            })

        # Fetch Credit Note vouchers from the generic Voucher table
        # (type='credit_note', party=customer_name, total=net_amount)
        cnote_qs = GenericVoucher.objects.filter(tenant_id=tenant_id, type='credit_note')
        if start_date:
            cnote_qs = cnote_qs.filter(date__gte=start_date)
        if end_date:
            cnote_qs = cnote_qs.filter(date__lte=end_date)
        for v in cnote_qs:
            vouchers.append({
                'date': v.date,
                'type': 'Credit Note',
                'voucher_number': v.voucher_number,
                'invoice_no': v.voucher_number,
                'party': v.party or '',
                'account': '',
                'total': float(v.total or 0),
                'amount': float(v.total or 0),
                'narration': v.narration or '',
                'id': v.id,
            })
        
        # Sort by date
        vouchers.sort(key=lambda x: x['date'])
        
        return vouchers

    def export_excel(self, df, filename):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        
        # Ensure we write bytes
        with io.BytesIO() as b:
            with pd.ExcelWriter(b, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            response.write(b.getvalue())
            
        return response

class DayBookExcelView(BaseExcelView):
    def get(self, request):
        vouchers = self.get_filtered_vouchers(request)
        
        data = []
        for v in vouchers:
            # v is now a dictionary
            amount = v.get('amount', 0)

            data.append({
                'Date': v['date'],
                'Voucher Type': v['type'],
                'Voucher Number': v['voucher_number'],
                'Party': v.get('party') or v.get('account') or '',
                'Amount': amount,
                'Narration': v.get('narration', '')
            })
            
        df = pd.DataFrame(data)
        if df.empty:
             df = pd.DataFrame(columns=['Date', 'Voucher Type', 'Voucher Number', 'Party', 'Amount', 'Narration'])
             
        return self.export_excel(df, 'DayBook.xlsx')

class LedgerExcelView(BaseExcelView):
    def get(self, request):
        ledger_name = request.query_params.get('ledger')
        if not ledger_name:
            # Return empty if no ledger selected
            df = pd.DataFrame(columns=['Date', 'Particulars', 'Voucher Type', 'Voucher No', 'Debit', 'Credit', 'Balance'])
            return self.export_excel(df, f'Ledger_Report.xlsx')
            
        vouchers = self.get_filtered_vouchers(request)
        
        data = []
        balance = 0
        
        for v in vouchers:
            debit = 0
            credit = 0
            particulars = ""
            
            # Logic based on voucher type
            if v['type'] == 'Sales':
                if v['party'] == ledger_name:
                    debit = v['amount']
                    particulars = "Sales"
                else:
                    credit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Purchase':
                if v['party'] == ledger_name:
                    credit = v['amount']
                    particulars = "Purchase"
                else:
                    debit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Receipt':
                if v['party'] == ledger_name:
                    credit = v['amount']
                    particulars = v['account']
                elif v['account'] == ledger_name:
                    debit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Payment':
                if v['party'] == ledger_name:
                    debit = v['amount']
                    particulars = v['account']
                elif v['account'] == ledger_name:
                    credit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Contra':
                if v['party'] == ledger_name:
                    credit = v['amount']
                    particulars = v['account']
                elif v['account'] == ledger_name:
                    debit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Journal':
                # For journal entries, would need to check journal_entries table
                # Simplified for now
                particulars = "Journal Entry"

            elif v['type'] == 'Debit Note':
                # Debit Note: reduces vendor liability (debit vendor, credit purchase return)
                if v['party'] == ledger_name:
                    # Vendor ledger – being DEBITED (liability reduced by return)
                    debit = v['amount']
                    particulars = "Purchase Return / Debit Note"
                elif ledger_name in ('Purchase Return', 'Purchase Return A/c', 'Purchases'):
                    # Purchase Return account – being CREDITED
                    credit = v['amount']
                    particulars = v['party']

            elif v['type'] == 'Credit Note':
                # Credit Note: reduces customer receivable (credit customer, debit sales return)
                if v['party'] == ledger_name:
                    # Customer ledger – being CREDITED (receivable reduced)
                    credit = v['amount']
                    particulars = "Sales Return / Credit Note"
                elif ledger_name in ('Sales Return', 'Sales Return A/c', 'Sales'):
                    # Sales Return account – being DEBITED
                    debit = v['amount']
                    particulars = v['party']
            
            # Only add row if this ledger was involved
            if debit > 0 or credit > 0:
                balance += (debit - credit)
                data.append({
                    'Date': v['date'],
                    'Particulars': particulars or v['type'],
                    'Voucher Type': v['type'],
                    'Voucher No': v['voucher_number'],
                    'Debit': debit,
                    'Credit': credit,
                    'Balance': balance
                })
            
        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=['Date', 'Particulars', 'Voucher Type', 'Voucher No', 'Debit', 'Credit', 'Balance'])

        return self.export_excel(df, f'Ledger_{ledger_name or "Report"}.xlsx')

class TrialBalanceExcelView(BaseExcelView):
    def get(self, request):
        """Trial Balance using JournalEntry as the authoritative accounting source."""
        from django.db.models import Sum
        from accounting.models import JournalEntry

        tenant_id = request.tenant_id
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')

        entries = JournalEntry.objects.filter(tenant_id=tenant_id)
        if start_date:
            entries = entries.filter(transaction_date__gte=start_date)
        if end_date:
            entries = entries.filter(transaction_date__lte=end_date)

        balances = entries.values('ledger__name').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('ledger__name')

        data = []
        total_debit = 0.0
        total_credit = 0.0

        for item in balances:
            d = float(item['total_debit'] or 0)
            c = float(item['total_credit'] or 0)
            net = d - c
            net_debit = net if net > 0 else 0
            net_credit = abs(net) if net < 0 else 0
            if net_debit > 0.001 or net_credit > 0.001:
                data.append({
                    'Ledger': item['ledger__name'] or '(Unlinked)',
                    'Debit': net_debit,
                    'Credit': net_credit
                })
                total_debit += net_debit
                total_credit += net_credit

        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=['Ledger', 'Debit', 'Credit'])

        if not df.empty:
            total_row = pd.DataFrame([{
                'Ledger': 'Total', 
                'Debit': total_debit, 
                'Credit': total_credit
            }])
            df = pd.concat([df, total_row], ignore_index=True)

        return self.export_excel(df, 'TrialBalance.xlsx')

class StockSummaryExcelView(BaseExcelView):
     def get(self, request):
        # Placeholder for stock summary
        df = pd.DataFrame(columns=['Item Name', 'Opening', 'Inward', 'Outward', 'Closing'])
        return self.export_excel(df, 'StockSummary.xlsx')

class GSTReportExcelView(BaseExcelView):
    def get(self, request):
        # Placeholder for GST
        df = pd.DataFrame(columns=['GSTIN', 'Party Name', 'Invoice No', 'Date', 'Value', 'Tax'])
        return self.export_excel(df, 'GSTReport.xlsx')

@method_decorator(csrf_exempt, name='dispatch')
class AIReportExcelView(BaseExcelView):
    def post(self, request):
        query = request.data.get('query')
        if not query:
            return Response({'error': 'Query is required'}, status=400)
            
        if not api_key_manager.api_keys:
             return Response({'error': 'AI service not available'}, status=503)

        try:
            from .ai_proxy import execute_with_retry
            
            # Get healthy key from manager
            api_key = api_key_manager.get_healthy_key()
            if not api_key:
                 return Response({'error': 'AI service busy (No healthy keys)'}, status=503)

            # 1. Ask AI to interpret the query into parameters
            current_date = datetime.date.today().isoformat()
            prompt = f"""
            You are a smart accounting assistant. The user wants to download an Excel report.
            Current Date: {current_date}
            User Query: "{query}"
            
            Extract the following parameters in JSON format:
            - report_type: One of ['sales', 'purchase', 'payment', 'receipt', 'ledger', 'daybook'] (default 'daybook')
            - start_date: YYYY-MM-DD (calculate if user says 'last month', 'this week', etc. Default to first day of current month if unspecified)
            - end_date: YYYY-MM-DD (calculate if necessary. Default to today if unspecified)
            - party_name: Name of specific customer/vendor/ledger if mentioned (or null)
            
            Return ONLY the JSON.
            """
            
            text = execute_with_retry(prompt, {}, api_key)
            text = text.replace('```json', '').replace('```', '').strip()
            params = json.loads(text)
            
            # 2. Map params to request query params
            # We mock the request parameters for re-using `get_filtered_vouchers` or custom logic
            request.GET._mutable = True
            request.query_params._mutable = True
            
            if params.get('start_date'):
                request.query_params['startDate'] = params['start_date']
            if params.get('end_date'):
                request.query_params['endDate'] = params['end_date']
            
            report_type = params.get('report_type', 'daybook').lower()
            party_name = params.get('party_name')
            
            # 3. Fetch Data
            # Note: get_filtered_vouchers returns a list of dictionaries
            vouchers = self.get_filtered_vouchers(request)
            
            # 4. Filter by type/party if needed (since get_filtered_vouchers gets EVERYTHING by default)
            filtered_vouchers = []
            
            for v in vouchers:
                # Type Filter
                if report_type == 'sales' and v['type'] != 'Sales': continue
                if report_type == 'purchase' and v['type'] != 'Purchase': continue
                if report_type == 'payment' and v['type'] != 'Payment': continue
                if report_type == 'receipt' and v['type'] != 'Receipt': continue
                
                # Party Filter (fuzzy match or exact?) 
                # Simple exact match or "in" string for now needed? 
                # AI extracted 'party_name', let's filter if it matches somewhat
                if party_name:
                    p = (v.get('party') or '').lower()
                    a = (v.get('account') or '').lower()
                    pn = party_name.lower()
                    if pn not in p and pn not in a:
                        continue
                        
                filtered_vouchers.append(v)
            
            # 5. Convert to Pandas DataFrame suitable for Excel
            data = []
            for v in filtered_vouchers:
                row = {
                    'Date': v['date'],
                    'Type': v['type'],
                    'Voucher No': v['voucher_number'],
                    'Party': v.get('party') or v.get('account'),
                    'Amount': v.get('amount') or v.get('total'),
                    'Narration': v.get('narration', '')
                }
                data.append(row)
                
            df = pd.DataFrame(data)
            if df.empty:
                # Return empty with headers
                df = pd.DataFrame(columns=['Date', 'Type', 'Voucher No', 'Party', 'Amount', 'Narration'])
            
            # 6. Return Excel
            filename = f"AI_{report_type.title()}_Report_{current_date}.xlsx"
            return self.export_excel(df, filename)

        except Exception as e:
            return Response({'error': str(e)}, status=500)

# =============================================================================
# Phase 5: Additive JSON API Views
# These views call the shared reports flow service layer (reports.flow).
# They are additive — they do NOT modify any existing Excel or API views.
# =============================================================================

class DaybookReportView(BaseExcelView):
    """JSON API for Day Book report — uses the same get_filtered_vouchers as Excel export."""

    def get(self, request):
        try:
            vouchers = self.get_filtered_vouchers(request)
            data = []
            for v in vouchers:
                data.append({
                    'date': str(v['date']),
                    'type': v.get('type', ''),
                    'voucher_number': v.get('voucher_number') or v.get('invoice_no') or '',
                    'party': v.get('party') or v.get('account') or '',
                    'amount': float(v.get('amount') or v.get('total') or 0),
                    'narration': v.get('narration') or '',
                })
            return Response({'results': data, 'count': len(data)})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


class TrialBalanceReportView(APIView):
    """JSON API for Trial Balance — uses JournalEntry as authoritative source."""
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get(self, request):
        from reports.flow import generate_trial_balance_data
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        try:
            tb = generate_trial_balance_data(request.user, start_date, end_date)
            total_debit = sum(r['debit'] for r in tb)
            total_credit = sum(r['credit'] for r in tb)
            return Response({
                'results': tb,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'is_balanced': abs(total_debit - total_credit) < 0.01,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class BalanceSheetReportView(APIView):
    """JSON API for Balance Sheet — uses ledger classification from Chart of Accounts."""
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get(self, request):
        from reports.flow import generate_balance_sheet_data
        end_date = request.query_params.get('endDate')
        try:
            bs = generate_balance_sheet_data(request.user, end_date)
            return Response(bs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


class StockSummaryReportView(APIView):
    """JSON API for Stock Summary — uses inventory stock movement data."""
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get(self, request):
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        try:
            from inventory.models import InventoryStockItem, StockMovement
            from django.db.models import Sum

            tenant_id = request.tenant_id
            items = InventoryStockItem.objects.filter(tenant_id=tenant_id)

            movements_qs = StockMovement.objects.filter(tenant_id=tenant_id)
            if start_date:
                movements_qs = movements_qs.filter(date__gte=start_date)
            if end_date:
                movements_qs = movements_qs.filter(date__lte=end_date)

            inward_agg = movements_qs.filter(movement_type='IN').values('item_id').annotate(total=Sum('quantity'))
            outward_agg = movements_qs.filter(movement_type='OUT').values('item_id').annotate(total=Sum('quantity'))

            inward_map = {r['item_id']: float(r['total'] or 0) for r in inward_agg}
            outward_map = {r['item_id']: float(r['total'] or 0) for r in outward_agg}

            data = []
            for item in items:
                inward = inward_map.get(item.id, 0)
                outward = outward_map.get(item.id, 0)
                opening = float(getattr(item, 'opening_balance', 0) or 0)
                closing = opening + inward - outward
                data.append({
                    'name': item.name,
                    'unit': getattr(item, 'unit', ''),
                    'opening': opening,
                    'inward': inward,
                    'outward': outward,
                    'closing': closing,
                })

            return Response({'results': data, 'count': len(data)})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
