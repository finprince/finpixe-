from rest_framework import viewsets, status
import pandas as pd
import io
import json
from django.http import HttpResponse, FileResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Q, Count, Min, Max
from accounting.models_voucher_sales import VoucherSalesInvoiceDetails, VoucherSalesItems
from accounting.models import AdvanceAllocation
from core.mixins import IsBranchMember

def get_payment_details(v):
    try:
        return v.payment_details
    except Exception:
        return None

class GSTR1ViewSet(viewsets.ViewSet):
    """
    ViewSet for generating GSTR1 return data.
    """
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get_queryset(self, include_cancelled=False):
        user = self.request.user
        tenant_id = getattr(user, 'tenant_id', None)
        if tenant_id:
            queryset = VoucherSalesInvoiceDetails.objects.filter(tenant_id=tenant_id)
        else:
            queryset = VoucherSalesInvoiceDetails.objects.all()
        year_str = self.request.query_params.get('year')
        month_str = self.request.query_params.get('month')
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        queryset = queryset.filter(date__year=filter_year, date__month=month_num)
            except Exception:
                pass
        if not include_cancelled:
            queryset = queryset.exclude(status='cancelled')
        return queryset

    @action(detail=False, methods=['get'])
    def b2b(self, request):
        """Get B2B invoices (Registered Customers) - excludes amended vouchers (those move to B2BA)"""
        vouchers = self.get_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').filter(amendment_date__isnull=True)
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            pos = ''
            if v.gstin and len(v.gstin) >= 2:
                pos = v.gstin[:2]
            elif v.state_type == 'within':
                pos = '29'
            elif v.state_type == 'other':
                pos = '27'
            data.append({'id': v.id, 'gstin': v.gstin, 'recipient_name': v.customer_name, 'invoice_no': v.sales_invoice_no, 'invoice_date': v.date, 'invoice_value': val, 'place_of_supply': pos, 'reverse_charge': 'N', 'taxable_value': taxable, 'igst': igst, 'cgst': cgst, 'sgst': sgst, 'rate': 0, 'gst_registered': v.gst_registered, 'amendment_date': v.amendment_date})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2ba(self, request):
        """Get B2BA invoices - shows original GST filed values for amended vouchers"""
        print('B2BA ENDPOINT HIT!')
        vouchers = self.get_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(amendment_date__isnull=True)
        print('VOUCHERS COUNT FOR B2BA:', vouchers.count())
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            pay = get_payment_details(v)
            orig_pay = snap.get('payment_details', {})
            if orig_pay:
                orig_val = orig_pay.get('payment_invoice_value', 0)
                orig_taxable = orig_pay.get('payment_taxable_value', 0)
                orig_igst = orig_pay.get('payment_igst', 0)
                orig_cgst = orig_pay.get('payment_cgst', 0)
                orig_sgst = orig_pay.get('payment_sgst', 0)
            else:
                pay_fallback = get_payment_details(v)
                orig_val = pay_fallback.payment_invoice_value if pay_fallback else 0
                orig_taxable = pay_fallback.payment_taxable_value if pay_fallback else 0
                orig_igst = pay_fallback.payment_igst if pay_fallback else 0
                orig_cgst = pay_fallback.payment_cgst if pay_fallback else 0
                orig_sgst = pay_fallback.payment_sgst if pay_fallback else 0
            orig_invoice_no = snap.get('sales_invoice_no', v.sales_invoice_no)
            orig_date = snap.get('date', str(v.date))
            orig_gstin = snap.get('gstin', v.gstin)
            orig_customer = snap.get('customer_name', v.customer_name)
            orig_pos = orig_gstin[:2] if orig_gstin and len(orig_gstin) >= 2 else pos
            pos = ''
            if v.gstin and len(v.gstin) >= 2:
                pos = v.gstin[:2]
            elif v.state_type == 'within':
                pos = '29'
            elif v.state_type == 'other':
                pos = '27'
            amended_val = pay.payment_invoice_value if pay else 0
            amended_taxable = pay.payment_taxable_value if pay else 0
            amended_igst = pay.payment_igst if pay else 0
            amended_cgst = pay.payment_cgst if pay else 0
            amended_sgst = pay.payment_sgst if pay else 0
            data.append({'id': v.id, 'gstin': orig_gstin, 'recipient_name': orig_customer, 'original_invoice_no': orig_invoice_no, 'original_invoice_date': orig_date, 'revised_invoice_no': v.sales_invoice_no, 'revised_invoice_date': str(v.amendment_date), 'invoice_value': orig_val, 'taxable_value': orig_taxable, 'igst': orig_igst, 'cgst': orig_cgst, 'sgst': orig_sgst, 'place_of_supply': orig_pos, 'reverse_charge': 'N', 'applicable_tax_rate': '', 'invoice_type': snap.get('invoice_type', 'Regular'), 'ecommerce_gstin': '', 'cess_amount': 0, 'rate': 0, 'has_snapshot': bool(snap), 'amended_invoice_no': v.sales_invoice_no, 'amended_invoice_date': str(v.date), 'amended_invoice_value': amended_val, 'amended_taxable_value': amended_taxable, 'rate': 0, 'revised_igst': amended_igst, 'revised_cgst': amended_cgst, 'revised_sgst': amended_sgst, 'source': 'b2ba_drilldown', 'amendment_filed': v.amendment_filed, 'amended_gstin': v.gstin, 'amended_recipient_name': v.customer_name, 'amended_place_of_supply': pos})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2cl(self, request):
        """Get B2C Large invoices (unregistered, >2.5L interstate, NOT amended)"""
        all_vouchers = self.get_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).filter(amendment_date__isnull=True)
        data = []
        for v in all_vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            if val <= 250000:
                continue
            if v.state_type != 'other':
                continue
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            pos = v.place_of_supply or '27'
            data.append({'id': v.id, 'invoice_no': v.sales_invoice_no, 'invoice_date': v.date, 'invoice_value': val, 'place_of_supply': pos, 'rate': 0, 'taxable_value': taxable, 'igst': igst, 'cess': 0, 'source': 'b2cl_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2cs(self, request):
        """Get B2C Small aggregated (excludes amended)"""
        all_vouchers = self.get_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).filter(amendment_date__isnull=True)
        agg_map = {}
        for v in all_vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            is_large_inter = val > 250000 and v.state_type == 'other'
            if is_large_inter:
                continue
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            pos = '29' if v.state_type == 'within' else '27'
            if pos not in agg_map:
                agg_map[pos] = {'taxable': 0, 'igst': 0, 'cgst': 0, 'sgst': 0, 'vouchers': []}
            agg_map[pos]['taxable'] += float(taxable)
            agg_map[pos]['igst'] += float(igst)
            agg_map[pos]['cgst'] += float(cgst)
            agg_map[pos]['sgst'] += float(sgst)
            agg_map[pos]['vouchers'].append({'id': v.id, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date), 'invoice_value': float(val), 'source': 'b2cs_drilldown', 'gst_registered': v.gst_registered, 'amendment_date': str(v.amendment_date) if v.amendment_date else None})
        data = []
        for pos, vals in agg_map.items():
            data.append({'type': 'OE', 'place_of_supply': pos, 'rate': 0, 'taxable_value': vals['taxable'], 'igst': vals['igst'], 'cgst': vals['cgst'], 'sgst': vals['sgst'], 'cess': 0, 'vouchers': vals['vouchers']})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2csa(self, request):
        """Get B2CSA aggregated (Amended B2C Small)"""
        all_vouchers = self.get_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(amendment_date__isnull=True)
        agg_map = {}
        for v in all_vouchers:
            snap = v.original_voucher_snapshot or {}
            orig_date_str = snap.get('date', str(v.date))
            orig_month = orig_date_str.split('-')[1] if '-' in orig_date_str else orig_date_str
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            is_large_inter = val > 250000 and v.state_type == 'other'
            if is_large_inter:
                continue
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            pos = '29' if v.state_type == 'within' else '27'
            orig_pos = pos
            if pos not in agg_map:
                agg_map[pos] = {'taxable': 0, 'igst': 0, 'cgst': 0, 'sgst': 0, 'orig_month': orig_month, 'orig_pos': orig_pos, 'vouchers': []}
            agg_map[pos]['taxable'] += float(taxable)
            agg_map[pos]['igst'] += float(igst)
            agg_map[pos]['cgst'] += float(cgst)
            agg_map[pos]['sgst'] += float(sgst)
            agg_map[pos]['vouchers'].append({'id': v.id, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date), 'invoice_value': float(val), 'source': 'b2csa_drilldown', 'gst_registered': v.gst_registered, 'amendment_date': str(v.amendment_date) if v.amendment_date else None, 'amendment_filed': v.amendment_filed})
        data = []
        for pos, vals in agg_map.items():
            data.append({'type': 'OE', 'original_month': vals['orig_month'], 'financial_year': '2026-27', 'original_pos': vals['orig_pos'], 'revised_pos': pos, 'rate': 0, 'original_rate': 0, 'taxable_value': vals['taxable'], 'cess': 0, 'ecommerce_gstin': '', 'vouchers': vals['vouchers']})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2cla(self, request):
        """Get B2CLA - Amended B2C Large invoices (unregistered, >2.5L interstate, amended)"""
        all_vouchers = self.get_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(amendment_date__isnull=True)
        data = []
        for v in all_vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            if val <= 250000:
                continue
            if v.state_type != 'other':
                continue
            snap = v.original_voucher_snapshot or {}
            orig_pay = snap.get('payment_details', {})
            orig_val = orig_pay.get('payment_invoice_value', val)
            orig_taxable = orig_pay.get('payment_taxable_value', 0)
            orig_igst = orig_pay.get('payment_igst', 0)
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            orig_invoice_no = snap.get('sales_invoice_no', v.sales_invoice_no)
            orig_date = snap.get('date', str(v.date))
            orig_pos = snap.get('place_of_supply', v.place_of_supply or '27')
            curr_pos = v.place_of_supply or '27'
            data.append({'id': v.id, 'original_invoice_no': orig_invoice_no, 'original_invoice_date': orig_date, 'original_invoice_value': orig_val, 'original_place_of_supply': orig_pos, 'original_taxable_value': orig_taxable, 'original_igst': orig_igst, 'revised_invoice_no': v.sales_invoice_no, 'revised_invoice_date': str(v.date), 'revised_invoice_value': val, 'revised_place_of_supply': curr_pos, 'revised_taxable_value': taxable, 'revised_igst': igst, 'amendment_date': str(v.amendment_date), 'amendment_filed': v.amendment_filed, 'rate': 0, 'cess': 0, 'source': 'b2cla_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecoaurp2b(self, request):
        """Get Amended URP B2B supplies through E-Commerce (Table 15B I(a) - ECOAURP2B)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            orig_pay = snap.get('payment_details', {})
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            orig_pos = snap.get('place_of_supply', '')
            pos = v.place_of_supply or ''
            orig_taxable = orig_pay.get('payment_taxable_value', 0) if orig_pay else 0
            rate = 0
            items = v.items.all() if hasattr(v, 'items') else []
            if items:
                try:
                    rate = max((float(item.gst_rate) for item in items if getattr(item, 'gst_rate', 0)))
                except (ValueError, TypeError):
                    rate = 0
            data.append({'id': v.id, 'supplier_name': v.third_party_supplier_name, 'original_invoice_no': snap.get('sales_invoice_no', snap.get('invoice_no', '')), 'original_invoice_date': snap.get('date', snap.get('invoice_date', '')), 'original_pos': orig_pos, 'revised_invoice_no': v.sales_invoice_no or v.invoice_no, 'revised_invoice_date': str(v.date) if v.date else str(v.invoice_date) if v.invoice_date else '', 'revised_customer_gstin': v.gstin, 'revised_customer_name': v.customer_name, 'revised_pos': pos, 'ecommerce_gstin': v.ecommerce_gstin, 'rate': rate, 'original_taxable_value': float(orig_taxable), 'revised_taxable_value': float(taxable), 'igst': float(igst), 'cgst': float(cgst), 'sgst': float(sgst), 'cess': float(cess), 'source': 'ecoaurp2b_drilldown', 'is_ecommerce_operator': True, 'is_ecommerce_sales': True})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecoaurp2c(self, request):
        """Get Amended URP B2C supplies through E-Commerce (Table 15B I(b) - ECOAURP2C)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            orig_pay = snap.get('payment_details', {})
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            orig_pos = snap.get('place_of_supply', '')
            pos = v.place_of_supply or ''
            orig_taxable = orig_pay.get('payment_taxable_value', 0) if orig_pay else 0
            rate = 0
            items = v.items.all() if hasattr(v, 'items') else []
            if items:
                try:
                    rate = max((float(item.gst_rate) for item in items if getattr(item, 'gst_rate', 0)))
                except (ValueError, TypeError):
                    rate = 0
            data.append({'id': v.id, 'supplier_name': v.third_party_supplier_name, 'original_invoice_no': snap.get('sales_invoice_no', snap.get('invoice_no', '')), 'original_invoice_date': snap.get('date', snap.get('invoice_date', '')), 'original_pos': orig_pos, 'revised_invoice_no': v.sales_invoice_no or v.invoice_no, 'revised_invoice_date': str(v.date) if v.date else str(v.invoice_date) if v.invoice_date else '', 'revised_pos': pos, 'ecommerce_gstin': v.ecommerce_gstin, 'rate': rate, 'original_taxable_value': float(orig_taxable), 'revised_taxable_value': float(taxable), 'igst': float(igst), 'cgst': float(cgst), 'sgst': float(sgst), 'cess': float(cess), 'source': 'ecoaurp2c_drilldown', 'is_ecommerce_operator': True, 'is_ecommerce_sales': True})
        return Response(data)

    @action(detail=False, methods=['get'])
    def exp(self, request):
        """Get Export invoices — excludes amended exports (those move to EXPA)"""
        vouchers = self.get_queryset().filter(state_type='export').filter(amendment_date__isnull=True)
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            data.append({'id': v.id, 'export_type': v.export_type or 'WPAY', 'invoice_no': v.sales_invoice_no, 'invoice_date': v.date, 'invoice_value': val, 'port_code': v.port_code or '', 'shipping_bill_number': v.shipping_bill_number or '', 'shipping_bill_date': v.shipping_bill_date or '', 'rate': 0, 'taxable_value': taxable})
        return Response(data)

    @action(detail=False, methods=['get'])
    def eco(self, request):
        """Get supplies made through E-Commerce Operators (Table 14 - ECO)"""
        vouchers = self.get_queryset().exclude(ecommerce_gstin__isnull=True).exclude(ecommerce_gstin__exact='').filter(amendment_date__isnull=True, is_ecommerce_operator=False)
        agg_map = {}
        for v in vouchers:
            pay = get_payment_details(v)
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            pos = v.place_of_supply
            if not pos:
                if v.gstin and len(v.gstin) >= 2:
                    pos = v.gstin[:2]
                elif v.state_type == 'within':
                    pos = '29'
                elif v.state_type == 'other':
                    pos = '27'
                else:
                    pos = '29'
            is_b2b = bool(v.gstin and v.gstin.strip() and (v.gstin.strip().lower() != 'unregistered'))
            nature = 'B2B' if is_b2b else 'B2C'
            eco_gstin = v.ecommerce_gstin
            from accounting.models import MasterLedger
            eco_name = 'E-Commerce Operator'
            tenant_id = getattr(request.user, 'tenant_id', None)
            ledger_qs = MasterLedger.objects.filter(gstin=eco_gstin)
            if tenant_id:
                ledger_qs = ledger_qs.filter(tenant_id=tenant_id)
            eco_ledger = ledger_qs.first()
            if eco_ledger:
                eco_name = eco_ledger.name
            else:
                try:
                    from customerportal.database import CustomerMasterCustomerGSTDetails
                    gst_qs = CustomerMasterCustomerGSTDetails.objects.select_related('customer_basic_detail').filter(gstin=eco_gstin)
                    if tenant_id:
                        gst_qs = gst_qs.filter(tenant_id=tenant_id)
                    first_gst = gst_qs.first()
                    if first_gst and hasattr(first_gst, 'customer_basic_detail') and first_gst.customer_basic_detail:
                        eco_name = first_gst.customer_basic_detail.customer_name
                except Exception:
                    pass
            key = (eco_gstin, pos, nature)
            if key not in agg_map:
                agg_map[key] = {'nature_of_supply': nature, 'place_of_supply': pos, 'ecommerce_gstin': eco_gstin, 'ecommerce_name': eco_name, 'net_value': 0, 'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0, 'vouchers': []}
            agg_map[key]['net_value'] += float(taxable)
            agg_map[key]['igst'] += float(igst)
            agg_map[key]['cgst'] += float(cgst)
            agg_map[key]['sgst'] += float(sgst)
            agg_map[key]['cess'] += float(cess)
            pay = get_payment_details(v)
            agg_map[key]['vouchers'].append({'id': v.id, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date), 'invoice_value': float(pay.payment_invoice_value) if pay else 0, 'source': 'eco_drilldown'})
        data = []
        for key, vals in agg_map.items():
            data.append({'nature_of_supply': vals['nature_of_supply'], 'place_of_supply': f"{vals['place_of_supply']} ({vals['ecommerce_gstin']})", 'ecommerce_name': vals['ecommerce_name'], 'net_value': vals['net_value'], 'igst': vals['igst'], 'cgst': vals['cgst'], 'sgst': vals['sgst'], 'cess': vals['cess'], 'vouchers': vals['vouchers']})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecob2b(self, request):
        """Get B2B supplies made through E-Commerce Operators (Table 15A I(a) - ECO B2B)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True, amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            cess = pay.payment_cess if pay else 0
            pos = v.place_of_supply
            if not pos:
                pos = v.gstin[:2] if v.gstin and len(v.gstin) >= 2 else '29'
            supply_type = 'Inter-State' if v.state_type == 'other' else 'Intra-State'
            data.append({'id': v.id, 'ecommerce_gstin': v.ecommerce_gstin, 'supplier_gstin': v.third_party_supplier_gstin, 'recipient_gstin': v.gstin, 'recipient_name': v.customer_name, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date), 'invoice_value': float(val), 'place_of_supply': pos, 'supply_type': supply_type, 'document_type': 'Invoice', 'rate': 0, 'taxable_value': float(taxable), 'cess': float(cess), 'is_ecommerce_operator': True, 'is_ecommerce_sales': True, 'supplier_name': getattr(v, 'third_party_supplier_name', '')})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecob2c(self, request):
        """Get B2C supplies made through E-Commerce Operators (Table 15A I(b) - ECO B2C)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True, amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            taxable = pay.payment_taxable_value if pay else 0
            cess = pay.payment_cess if pay else 0
            pos = v.place_of_supply
            if not pos:
                pos = '29' if v.state_type == 'within' else '27'
            data.append({'id': v.id, 'ecommerce_gstin': v.ecommerce_gstin, 'supplier_gstin': v.third_party_supplier_gstin, 'supplier_name': v.third_party_supplier_name, 'place_of_supply': pos, 'rate': 0, 'taxable_value': float(taxable), 'cess': float(cess), 'is_ecommerce_operator': True, 'is_ecommerce_sales': True})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecourp2b(self, request):
        """Get supplies made through ECO to URP B2B (Table 15A II(a) - ECOURP2B)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True, amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            cess = pay.payment_cess if pay else 0
            pos = v.place_of_supply
            if not pos:
                pos = v.gstin[:2] if v.gstin and len(v.gstin) >= 2 else '29'
            supply_type = 'Inter-State' if v.state_type == 'other' else 'Intra-State'
            data.append({'id': v.id, 'ecommerce_gstin': v.ecommerce_gstin, 'supplier_gstin': '', 'recipient_gstin': v.gstin, 'recipient_name': v.customer_name, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date), 'invoice_value': float(val), 'place_of_supply': pos, 'supply_type': supply_type, 'document_type': 'Invoice', 'rate': 0, 'taxable_value': float(taxable), 'cess': float(cess), 'is_ecommerce_operator': True, 'is_ecommerce_sales': True, 'supplier_name': getattr(v, 'third_party_supplier_name', '')})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecourp2c(self, request):
        """Get supplies made through ECO to URP B2C (Table 15A II(b) - ECOURP2C)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True, amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        data = []
        for v in vouchers:
            pay = get_payment_details(v)
            taxable = pay.payment_taxable_value if pay else 0
            cess = pay.payment_cess if pay else 0
            pos = v.place_of_supply
            if not pos:
                pos = '29' if v.state_type == 'within' else '27'
            data.append({'id': v.id, 'ecommerce_gstin': v.ecommerce_gstin, 'supplier_gstin': '', 'supplier_name': v.third_party_supplier_name, 'place_of_supply': pos, 'rate': 0, 'taxable_value': float(taxable), 'cess': float(cess), 'is_ecommerce_operator': True, 'is_ecommerce_sales': True})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecoa(self, request):
        """Get Amended supplies made through E-Commerce Operators (Table 14A)"""
        vouchers = self.get_queryset().exclude(ecommerce_gstin__isnull=True).exclude(ecommerce_gstin__exact='').exclude(amendment_date__isnull=True).filter(is_ecommerce_operator=False)
        agg_map = {}
        for v in vouchers:
            pay = get_payment_details(v)
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            snap = v.original_voucher_snapshot or {}
            orig_eco_gstin = snap.get('ecommerce_gstin', v.ecommerce_gstin)
            orig_eco_name = orig_eco_gstin or ''
            curr_eco_name = v.ecommerce_gstin or ''
            key = (orig_eco_gstin, v.ecommerce_gstin)
            if key not in agg_map:
                agg_map[key] = {'original_ecommerce_gstin': orig_eco_gstin, 'original_ecommerce_name': orig_eco_name, 'ecommerce_gstin': v.ecommerce_gstin, 'ecommerce_name': curr_eco_name, 'taxable_value': 0, 'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0, 'vouchers': []}
            agg_map[key]['taxable_value'] += float(taxable)
            agg_map[key]['igst'] += float(igst)
            agg_map[key]['cgst'] += float(cgst)
            agg_map[key]['sgst'] += float(sgst)
            agg_map[key]['cess'] += float(cess)
            agg_map[key]['vouchers'].append({'id': v.id, 'invoice_no': v.sales_invoice_no, 'invoice_date': str(v.date) if v.date else '', 'invoice_value': float(pay.payment_invoice_value) if pay else 0, 'source': 'ecoa_drilldown'})
        data = list(agg_map.values())
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecoab2b(self, request):
        """Get Amended B2B supplies through E-Commerce (Table 15A I(a) - ECOAB2B)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(amendment_date__isnull=True)
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            orig_pay = snap.get('payment_details', {})
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            orig_pos = ''
            orig_gstin = snap.get('gstin', '')
            if orig_gstin and len(orig_gstin) >= 2:
                orig_pos = orig_gstin[:2]
            elif snap.get('place_of_supply'):
                orig_pos = snap.get('place_of_supply')
            pos = ''
            if v.gstin and len(v.gstin) >= 2:
                pos = v.gstin[:2]
            elif v.place_of_supply:
                pos = v.place_of_supply
            orig_taxable = orig_pay.get('payment_taxable_value', 0) if orig_pay else 0
            rate = 0
            items = v.items.all() if hasattr(v, 'items') else []
            if items:
                try:
                    rate = max((float(item.gst_rate) for item in items if getattr(item, 'gst_rate', 0)))
                except (ValueError, TypeError):
                    rate = 0
            data.append({'id': v.id, 'supplier_gstin': v.third_party_supplier_gstin, 'original_invoice_no': snap.get('sales_invoice_no', snap.get('invoice_no', '')), 'original_invoice_date': snap.get('date', snap.get('invoice_date', '')), 'original_customer_gstin': orig_gstin, 'original_customer_name': snap.get('customer_name', ''), 'original_pos': orig_pos, 'revised_invoice_no': v.sales_invoice_no or v.invoice_no, 'revised_invoice_date': str(v.date) if v.date else str(v.invoice_date) if v.invoice_date else '', 'revised_customer_gstin': v.gstin, 'revised_customer_name': v.customer_name, 'revised_pos': pos, 'ecommerce_gstin': v.ecommerce_gstin, 'rate': rate, 'original_taxable_value': float(orig_taxable), 'revised_taxable_value': float(taxable), 'igst': float(igst), 'cgst': float(cgst), 'sgst': float(sgst), 'cess': float(cess), 'source': 'ecoab2b_drilldown', 'is_ecommerce_operator': True, 'is_ecommerce_sales': True, 'supplier_name': getattr(v, 'third_party_supplier_name', '')})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ecoab2c(self, request):
        """Get Amended B2C supplies through E-Commerce (Table 15A I(b) - ECOAB2C)"""
        vouchers = self.get_queryset().filter(is_ecommerce_operator=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(amendment_date__isnull=True)
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            orig_pay = snap.get('payment_details', {})
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            cess = pay.payment_cess if pay else 0
            orig_pos = snap.get('place_of_supply', '')
            pos = v.place_of_supply or ''
            orig_taxable = orig_pay.get('payment_taxable_value', 0) if orig_pay else 0
            rate = 0
            items = v.items.all() if hasattr(v, 'items') else []
            if items:
                try:
                    rate = max((float(item.gst_rate) for item in items if getattr(item, 'gst_rate', 0)))
                except (ValueError, TypeError):
                    rate = 0
            data.append({'id': v.id, 'supplier_name': v.third_party_supplier_name, 'supplier_gstin': v.third_party_supplier_gstin, 'original_invoice_no': snap.get('sales_invoice_no', snap.get('invoice_no', '')), 'original_invoice_date': snap.get('date', snap.get('invoice_date', '')), 'original_pos': orig_pos, 'revised_invoice_no': v.sales_invoice_no or v.invoice_no, 'revised_invoice_date': str(v.date) if v.date else str(v.invoice_date) if v.invoice_date else '', 'revised_pos': pos, 'ecommerce_gstin': v.ecommerce_gstin, 'rate': rate, 'original_taxable_value': float(orig_taxable), 'revised_taxable_value': float(taxable), 'igst': float(igst), 'cgst': float(cgst), 'sgst': float(sgst), 'cess': float(cess), 'source': 'ecoab2c_drilldown', 'is_ecommerce_operator': True, 'is_ecommerce_sales': True})
        return Response(data)

    @action(detail=False, methods=['get'])
    def expa(self, request):
        """Get EXPA - Amended Export invoices (GST-filed exports that were later edited)"""
        vouchers = self.get_queryset().filter(state_type='export').exclude(amendment_date__isnull=True)
        data = []
        for v in vouchers:
            snap = v.original_voucher_snapshot or {}
            pay = get_payment_details(v)
            orig_pay = snap.get('payment_details', {})
            if orig_pay:
                orig_val = orig_pay.get('payment_invoice_value', 0)
                orig_taxable = orig_pay.get('payment_taxable_value', 0)
            else:
                orig_val = pay.payment_invoice_value if pay else 0
                orig_taxable = pay.payment_taxable_value if pay else 0
            orig_invoice_no = snap.get('sales_invoice_no', v.sales_invoice_no)
            orig_date = snap.get('date', str(v.date))
            orig_export_type = snap.get('export_type', v.export_type or 'WPAY')
            orig_port_code = snap.get('port_code', v.port_code or '')
            orig_sb_number = snap.get('shipping_bill_number', v.shipping_bill_number or '')
            orig_sb_date = snap.get('shipping_bill_date', v.shipping_bill_date or '')
            amended_val = pay.payment_invoice_value if pay else 0
            amended_taxable = pay.payment_taxable_value if pay else 0
            data.append({'id': v.id, 'has_snapshot': bool(snap), 'export_type': orig_export_type, 'original_invoice_no': orig_invoice_no, 'original_invoice_date': orig_date, 'invoice_value': orig_val, 'port_code': orig_port_code, 'shipping_bill_number': orig_sb_number, 'shipping_bill_date': str(orig_sb_date) if orig_sb_date else '', 'rate': 0, 'taxable_value': orig_taxable, 'revised_invoice_no': v.sales_invoice_no, 'revised_invoice_date': str(v.amendment_date), 'revised_invoice_value': amended_val, 'revised_taxable_value': amended_taxable, 'revised_export_type': v.export_type or 'WPAY', 'revised_port_code': v.port_code or '', 'revised_shipping_bill_number': v.shipping_bill_number or '', 'revised_shipping_bill_date': str(v.shipping_bill_date) if v.shipping_bill_date else '', 'amendment_filed': v.amendment_filed})
        return Response(data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Returns counts for each GSTR1 category for the selected period"""
        queryset = self.get_queryset()
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        b2b_count = queryset.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').filter(amendment_date__isnull=True).count()
        b2ba_count = queryset.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(amendment_date__isnull=True).count()
        unreg = queryset.filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        b2cl_count = 0
        b2cla_count = 0
        b2cs_count = 0
        b2csa_count = 0
        for v in unreg:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            is_large_inter = val > 250000 and v.state_type == 'other'
            if is_large_inter:
                if v.amendment_date is not None:
                    b2cla_count += 1
                else:
                    b2cl_count += 1
            elif v.amendment_date is not None:
                b2csa_count += 1
            else:
                b2cs_count += 1
        exp_count = queryset.filter(state_type='export').filter(amendment_date__isnull=True).count()
        expa_count = queryset.filter(state_type='export').exclude(amendment_date__isnull=True).count()
        atadj_count = 0
        atadja_count = 0
        for v in queryset:
            snap = v.original_voucher_snapshot or {}
            pay = get_payment_details(v)
            orig_pay = snap.get('payment_details', {})
            orig_advance = float(orig_pay.get('payment_advance', 0)) if orig_pay else 0
            amended_advance = float(pay.payment_advance) if pay and pay.payment_advance else 0
            if v.amendment_date is not None:
                if orig_advance > 0 or amended_advance > 0:
                    atadja_count += 1
            elif amended_advance > 0:
                atadj_count += 1
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        doc_count = self.get_queryset(include_cancelled=True).count()
        cn_qs = VoucherCreditNoteInvoiceDetails.objects.all()
        if tenant_id:
            cn_qs = cn_qs.filter(tenant_id=tenant_id)
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year_cn = int(year_str.split('-')[0])
                    end_year_cn = start_year_cn + 1
                    months_map_cn = {'April': (4, start_year_cn), 'May': (5, start_year_cn), 'June': (6, start_year_cn), 'July': (7, start_year_cn), 'August': (8, start_year_cn), 'September': (9, start_year_cn), 'October': (10, start_year_cn), 'November': (11, start_year_cn), 'December': (12, start_year_cn), 'January': (1, end_year_cn), 'February': (2, end_year_cn), 'March': (3, end_year_cn)}
                    mn, fy = months_map_cn.get(month_str, (None, None))
                    if mn and fy:
                        cn_qs = cn_qs.filter(date__year=fy, date__month=mn)
            except Exception:
                pass
        cdnr_count = cn_qs.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').filter(amendment_date__isnull=True).count()
        cdnra_count = cn_qs.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(amendment_date__isnull=True).count()
        cdnur_count = cn_qs.filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).filter(amendment_date__isnull=True).count()
        cdnura_count = cn_qs.filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(amendment_date__isnull=True).count()
        eco_count = queryset.exclude(ecommerce_gstin__isnull=True).exclude(ecommerce_gstin__exact='').filter(amendment_date__isnull=True, is_ecommerce_operator=False).count()
        ecob2b_count = queryset.filter(is_ecommerce_operator=True, amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').count()
        ecob2c_count = queryset.filter(is_ecommerce_operator=True, amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).count()
        ecoa_count = queryset.exclude(ecommerce_gstin__isnull=True).exclude(ecommerce_gstin__exact='').exclude(amendment_date__isnull=True).filter(is_ecommerce_operator=False).count()
        ecoab2b_count = queryset.filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').count()
        ecoab2c_count = queryset.filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).exclude(third_party_supplier_gstin__isnull=True).exclude(third_party_supplier_gstin__exact='').filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).count()
        ecourp2b_count = queryset.filter(is_ecommerce_operator=True, amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').count()
        ecourp2c_count = queryset.filter(is_ecommerce_operator=True, amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).count()
        ecoaurp2b_count = queryset.filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').count()
        ecoaurp2c_count = queryset.filter(is_ecommerce_operator=True).exclude(amendment_date__isnull=True).filter(Q(third_party_supplier_gstin__isnull=True) | Q(third_party_supplier_gstin__exact='')).filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).count()
        from accounting.models import AdvanceAllocation
        from decimal import Decimal
        at_count = 0
        ata_count = 0
        try:
            advances = AdvanceAllocation.objects.filter(tenant_id=tenant_id, transaction__transaction_type='RECEIPT')
            if 'fy' in locals() and 'mn' in locals() and fy and mn:
                at_advances = advances.filter(transaction__date__year=fy, transaction__date__month=mn, amendment_date__isnull=True)
                ata_advances = advances.filter(transaction__date__year=fy, transaction__date__month=mn, amendment_date__isnull=False, gst_registered='Yes')
            else:
                at_advances = advances.filter(amendment_date__isnull=True)
                ata_advances = advances.filter(amendment_date__isnull=False, gst_registered='Yes')
            for adv in at_advances:
                if Decimal(str(adv.amount)) > 0:
                    at_count += 1
            for adv in ata_advances:
                if Decimal(str(adv.amount)) > 0:
                    ata_count += 1
        except Exception:
            pass
        return Response({'B2B': b2b_count, 'B2BA': b2ba_count, 'B2CL': b2cl_count, 'B2CLA': b2cla_count, 'B2CS': b2cs_count, 'B2CSA': b2csa_count, 'EXP': exp_count, 'EXPA': expa_count, 'ATADJ': atadj_count, 'ATADJA': atadja_count, 'AT': at_count, 'ATA': ata_count, 'DOC': doc_count, 'CDNR': cdnr_count, 'CDNRA': cdnra_count, 'CDNUR': cdnur_count, 'CDNURA': cdnura_count, 'AT': at_count, 'HSN': 0, 'ECO': eco_count, 'ECOB2B': ecob2b_count, 'ECOB2C': ecob2c_count, 'ECOA': ecoa_count, 'ECOURP2B': ecourp2b_count, 'ECOURP2C': ecourp2c_count, 'ECOAB2B': ecoab2b_count, 'ECOAB2C': ecoab2c_count, 'ECOAURP2B': ecoaurp2b_count, 'ECOAURP2C': ecoaurp2c_count})

    @action(detail=False, methods=['get'])
    def cdnr(self, request):
        """Get CDNR - Credit/Debit Notes (Registered)
        Pulls Credit Notes issued to customers with a valid GSTIN for the selected period.
        """
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails, VoucherCreditNoteItemDetails
        from decimal import Decimal
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        print(f'[CDNR DEBUG] user={user}, tenant_id={tenant_id}, year={year_str}, month={month_str}')
        qs = VoucherCreditNoteInvoiceDetails.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        print(f'[CDNR DEBUG] total CNs for tenant: {qs.count()}')
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        qs = qs.filter(date__year=filter_year, date__month=month_num)
            except Exception:
                pass
        qs = qs.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').filter(amendment_date__isnull=True)
        data = []
        for cn in qs:
            try:
                item_det = cn.item_details
                total_taxable = float(item_det.total_taxable_value or 0)
                total_igst = float(item_det.total_igst or 0)
                total_cgst = float(item_det.total_cgst or 0)
                total_sgst = float(item_det.total_sgst or 0)
                total_cess = float(item_det.total_cess or 0)
                note_value = float(item_det.total_invoice_value or 0)
            except Exception:
                total_taxable = total_igst = total_cgst = total_sgst = total_cess = note_value = 0
            pos = ''
            if cn.gstin and len(cn.gstin) >= 2:
                pos = cn.gstin[:2]
            note_supply_type = 'Intra-State'
            if total_igst > 0:
                note_supply_type = 'Inter-State'
            data.append({'id': cn.id, 'gstin': cn.gstin, 'recipient_name': cn.customer_name, 'note_number': cn.credit_note_no, 'note_date': str(cn.date), 'note_type': 'C', 'place_of_supply': pos, 'reverse_charge': 'N', 'note_supply_type': note_supply_type, 'note_value': note_value, 'applicable_tax_rate': '', 'rate': 0, 'taxable_value': total_taxable, 'igst': total_igst, 'cgst': total_cgst, 'sgst': total_sgst, 'cess': total_cess, 'sales_invoice_nos': cn.sales_invoice_nos or '', 'gst_registered': getattr(cn, 'gst_registered', '') or ''})
        return Response(data)

    @action(detail=False, methods=['get'])
    def cdnur(self, request):
        """Get CDNUR - Credit/Debit Notes (Unregistered)
        Pulls Credit Notes issued to customers WITHOUT a GSTIN for the selected period.
        """
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        qs = VoucherCreditNoteInvoiceDetails.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        qs = qs.filter(date__year=filter_year, date__month=month_num)
            except Exception:
                pass
        qs = qs.filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).filter(amendment_date__isnull=True)
        data = []
        for cn in qs:
            try:
                item_det = cn.item_details
                total_taxable = float(item_det.total_taxable_value or 0)
                total_igst = float(item_det.total_igst or 0)
                total_cgst = float(item_det.total_cgst or 0)
                total_sgst = float(item_det.total_sgst or 0)
                total_cess = float(item_det.total_cess or 0)
                note_value = float(item_det.total_invoice_value or 0)
            except Exception:
                total_taxable = total_igst = total_cgst = total_sgst = total_cess = note_value = 0
            note_supply_type = 'Intra-State'
            if total_igst > 0:
                note_supply_type = 'Inter-State'
            data.append({'id': cn.id, 'recipient_name': cn.customer_name, 'note_type': 'C', 'note_supply_type': note_supply_type, 'note_number': cn.credit_note_no, 'note_date': str(cn.date), 'note_value': note_value, 'applicable_tax_rate': '', 'rate': 0, 'taxable_value': total_taxable, 'igst': total_igst, 'cgst': total_cgst, 'sgst': total_sgst, 'cess': total_cess, 'sales_invoice_nos': cn.sales_invoice_nos or '', 'gst_registered': getattr(cn, 'gst_registered', '') or ''})
        return Response(data)

    @action(detail=False, methods=['get'])
    def cdnra(self, request):
        """Get CDNRA - Credit/Debit Notes (Registered) Amendment
        Pulls Credit Notes issued to customers with a valid GSTIN that have been amended.
        """
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        from decimal import Decimal
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        qs = VoucherCreditNoteInvoiceDetails.objects.filter(amendment_date__isnull=False)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        qs = qs.filter(date__year=filter_year, date__month=month_num)
            except Exception:
                pass
        qs = qs.exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        data = []
        for cn in qs:
            snap = cn.original_voucher_snapshot or {}
            orig_note_no = snap.get('credit_note_no', cn.credit_note_no)
            orig_date = snap.get('date', str(cn.date))
            orig_gstin = snap.get('gstin', cn.gstin)
            orig_customer = snap.get('customer_name', cn.customer_name)
            orig_item_det = snap.get('item_details', {})
            orig_val = float(orig_item_det.get('total_invoice_value', 0) if orig_item_det else 0)
            orig_taxable = float(orig_item_det.get('total_taxable_value', 0) if orig_item_det else 0)
            orig_igst = float(orig_item_det.get('total_igst', 0) if orig_item_det else 0)
            orig_cgst = float(orig_item_det.get('total_cgst', 0) if orig_item_det else 0)
            orig_sgst = float(orig_item_det.get('total_sgst', 0) if orig_item_det else 0)
            orig_cess = float(orig_item_det.get('total_cess', 0) if orig_item_det else 0)
            try:
                item_det = cn.item_details
                amended_val = float(item_det.total_invoice_value or 0)
                amended_taxable = float(item_det.total_taxable_value or 0)
                amended_igst = float(item_det.total_igst or 0)
                amended_cgst = float(item_det.total_cgst or 0)
                amended_sgst = float(item_det.total_sgst or 0)
                amended_cess = float(item_det.total_cess or 0)
            except Exception:
                amended_val = amended_taxable = amended_igst = amended_cgst = amended_sgst = amended_cess = 0
            pos = ''
            if cn.gstin and len(cn.gstin) >= 2:
                pos = cn.gstin[:2]
            orig_pos = orig_gstin[:2] if orig_gstin and len(orig_gstin) >= 2 else pos
            data.append({'id': cn.id, 'gstin': orig_gstin, 'recipient_name': orig_customer, 'original_note_number': orig_note_no, 'original_note_date': orig_date, 'revised_note_number': cn.credit_note_no, 'revised_note_date': str(cn.amendment_date), 'note_value': orig_val, 'taxable_value': orig_taxable, 'igst': orig_igst, 'cgst': orig_cgst, 'sgst': orig_sgst, 'cess': orig_cess, 'place_of_supply': orig_pos, 'reverse_charge': 'N', 'applicable_tax_rate': '', 'rate': 0, 'has_snapshot': bool(snap), 'amended_note_number': cn.credit_note_no, 'amended_note_date': str(cn.date), 'amended_note_value': amended_val, 'amended_taxable_value': amended_taxable, 'revised_igst': amended_igst, 'revised_cgst': amended_cgst, 'revised_sgst': amended_sgst, 'revised_cess': amended_cess, 'source': 'cdnra_drilldown', 'amendment_filed': cn.amendment_filed, 'amended_gstin': cn.gstin, 'amended_recipient_name': cn.customer_name, 'amended_place_of_supply': pos, 'gst_registered': getattr(cn, 'gst_registered', '') or ''})
        return Response(data)

    @action(detail=False, methods=['get'])
    def cdnura(self, request):
        """Get CDNURA - Credit/Debit Notes (Unregistered) Amendment
        Pulls Credit Notes issued to unregistered customers (no GSTIN) that have been amended.
        """
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        from django.db.models import Q
        from decimal import Decimal
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        qs = VoucherCreditNoteInvoiceDetails.objects.filter(amendment_date__isnull=False)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        qs = qs.filter(date__year=filter_year, date__month=month_num)
            except Exception:
                pass
        qs = qs.filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        data = []
        for cn in qs:
            snap = cn.original_voucher_snapshot or {}
            orig_note_no = snap.get('credit_note_no', cn.credit_note_no)
            orig_date = snap.get('date', str(cn.date))
            orig_gstin = snap.get('gstin', cn.gstin)
            orig_customer = snap.get('customer_name', cn.customer_name)
            orig_item_det = snap.get('item_details', {})
            orig_val = float(orig_item_det.get('total_invoice_value', 0) if orig_item_det else 0)
            orig_taxable = float(orig_item_det.get('total_taxable_value', 0) if orig_item_det else 0)
            orig_igst = float(orig_item_det.get('total_igst', 0) if orig_item_det else 0)
            orig_cgst = float(orig_item_det.get('total_cgst', 0) if orig_item_det else 0)
            orig_sgst = float(orig_item_det.get('total_sgst', 0) if orig_item_det else 0)
            orig_cess = float(orig_item_det.get('total_cess', 0) if orig_item_det else 0)
            try:
                item_det = cn.item_details
                amended_val = float(item_det.total_invoice_value or 0)
                amended_taxable = float(item_det.total_taxable_value or 0)
                amended_igst = float(item_det.total_igst or 0)
                amended_cgst = float(item_det.total_cgst or 0)
                amended_sgst = float(item_det.total_sgst or 0)
                amended_cess = float(item_det.total_cess or 0)
            except Exception:
                amended_val = amended_taxable = amended_igst = amended_cgst = amended_sgst = amended_cess = 0
            pos = ''
            if cn.gstin and len(cn.gstin) >= 2:
                pos = cn.gstin[:2]
            orig_pos = orig_gstin[:2] if orig_gstin and len(orig_gstin) >= 2 else pos
            data.append({'id': cn.id, 'gstin': orig_gstin, 'recipient_name': orig_customer, 'original_note_number': orig_note_no, 'original_note_date': orig_date, 'revised_note_number': cn.credit_note_no, 'revised_note_date': str(cn.amendment_date), 'note_value': orig_val, 'taxable_value': orig_taxable, 'igst': orig_igst, 'cgst': orig_cgst, 'sgst': orig_sgst, 'cess': orig_cess, 'place_of_supply': orig_pos, 'reverse_charge': 'N', 'applicable_tax_rate': '', 'rate': 0, 'has_snapshot': bool(snap), 'amended_note_number': cn.credit_note_no, 'amended_note_date': str(cn.date), 'amended_note_value': amended_val, 'amended_taxable_value': amended_taxable, 'revised_igst': amended_igst, 'revised_cgst': amended_cgst, 'revised_sgst': amended_sgst, 'revised_cess': amended_cess, 'source': 'cdnur_drilldown', 'amendment_filed': cn.amendment_filed, 'amended_gstin': cn.gstin, 'amended_recipient_name': cn.customer_name, 'amended_place_of_supply': pos, 'gst_registered': getattr(cn, 'gst_registered', '') or ''})
        return Response(data)

    @action(detail=False, methods=['get'])
    def at(self, request):
        """Get AT - Advance Tax"""
        from decimal import Decimal
        from accounting.models import Transaction, AdvanceAllocation
        year_str = self.request.query_params.get('year')
        month_str = self.request.query_params.get('month')
        q_filter = {}
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        q_filter['transaction__date__year'] = filter_year
                        q_filter['transaction__date__month'] = month_num
            except Exception:
                pass
        advances = AdvanceAllocation.objects.filter(tenant_id=request.user.tenant_id if hasattr(request.user, 'tenant_id') else request.user.branch_id if hasattr(request.user, 'branch_id') else None, transaction__transaction_type='RECEIPT', amendment_date__isnull=True, **q_filter).select_related('transaction', 'pay_from_ledger')
        data = []
        for adv in advances:
            t = adv.transaction
            advance_amount = Decimal(str(adv.amount))
            if advance_amount <= 0:
                continue
            pos = ''
            customer_ledger = adv.pay_from_ledger
            if customer_ledger:
                from customerportal.database import CustomerMasterCustomerBasicDetails, CustomerMasterCustomerGSTDetails
                cust = CustomerMasterCustomerBasicDetails.objects.filter(ledger_id=customer_ledger.id).first()
                if cust:
                    gst_detail = CustomerMasterCustomerGSTDetails.objects.filter(customer_basic_detail=cust).first()
                    if gst_detail:
                        if gst_detail.gstin and len(gst_detail.gstin) >= 2:
                            pos = gst_detail.gstin[:2]
                        elif gst_detail.state:
                            pass
            if not pos:
                pos = '29'
            rate = Decimal(str(adv.gst_rate)) if adv.gst_rate is not None else Decimal('18.00')
            data.append({'voucher_id': t.id, 'voucher_no': t.voucher_number, 'place_of_supply': pos, 'rate': float(rate), 'gross_advance_received': float(advance_amount), 'cess_amount': 0.0, 'gst_registered': adv.gst_registered})
        return Response(data)

    @action(detail=False, methods=['get'])
    def ata(self, request):
        """Get ATA - Advance Tax (Amendment)"""
        from decimal import Decimal
        from accounting.models import AdvanceAllocation
        year_str = self.request.query_params.get('year')
        month_str = self.request.query_params.get('month')
        q_filter = {}
        if year_str and month_str:
            try:
                if '-' in year_str:
                    start_year = int(year_str.split('-')[0])
                    end_year = start_year + 1
                    months_map = {'April': (4, start_year), 'May': (5, start_year), 'June': (6, start_year), 'July': (7, start_year), 'August': (8, start_year), 'September': (9, start_year), 'October': (10, start_year), 'November': (11, start_year), 'December': (12, start_year), 'January': (1, end_year), 'February': (2, end_year), 'March': (3, end_year)}
                    month_num, filter_year = months_map.get(month_str, (None, None))
                    if month_num and filter_year:
                        q_filter['transaction__date__year'] = filter_year
                        q_filter['transaction__date__month'] = month_num
            except Exception:
                pass
        user_tenant = request.user.tenant_id if hasattr(request.user, 'tenant_id') else request.user.branch_id if hasattr(request.user, 'branch_id') else None
        advances = AdvanceAllocation.objects.filter(tenant_id=user_tenant, transaction__transaction_type='RECEIPT', gst_registered='Yes', amendment_date__isnull=False, **q_filter).select_related('transaction', 'pay_from_ledger')
        data = []
        for adv in advances:
            t = adv.transaction
            advance_amount = Decimal(str(adv.amount))
            if advance_amount <= 0:
                continue
            pos = ''
            customer_ledger = adv.pay_from_ledger
            if customer_ledger:
                from customerportal.database import CustomerMasterCustomerBasicDetails, CustomerMasterCustomerGSTDetails
                cust = CustomerMasterCustomerBasicDetails.objects.filter(ledger_id=customer_ledger.id).first()
                if cust:
                    gst_detail = CustomerMasterCustomerGSTDetails.objects.filter(customer_basic_detail=cust).first()
                    if gst_detail and gst_detail.gstin and (len(gst_detail.gstin) >= 2):
                        pos = gst_detail.gstin[:2]
            if not pos:
                pos = '29'
            rate = Decimal(str(adv.gst_rate)) if adv.gst_rate is not None else Decimal('18.00')
            snapshot = adv.original_voucher_snapshot or {}
            orig_rate_str = snapshot.get('original_rate', 18.0)
            orig_rate = float(orig_rate_str) if orig_rate_str else 18.0
            orig_amount_str = snapshot.get('original_amount', 0)
            orig_amount = float(orig_amount_str) if orig_amount_str else 0.0
            data.append({'voucher_id': t.id, 'voucher_no': t.voucher_number, 'original_month': snapshot.get('original_month', ''), 'original_year': snapshot.get('original_year', ''), 'original_pos': pos, 'original_rate': orig_rate, 'original_amount': orig_amount, 'revised_pos': pos, 'revised_rate': float(rate), 'revised_amount': float(advance_amount), 'cess_amount': 0.0, 'gst_registered': adv.gst_registered})
        return Response(data)

    @action(detail=False, methods=['get'])
    def atadj(self, request):
        """
        Get ATADJ - Advance Tax Adjustment
        Query vouchers where advance was used/adjusted and apportion across tax rates.
        """
        from decimal import Decimal
        queryset = self.get_queryset().filter(amendment_date__isnull=True)
        data = []
        for v in queryset:
            pay = get_payment_details(v)
            if pay and pay.payment_advance and (pay.payment_advance > 0):
                pos = ''
                if v.gstin and len(v.gstin) >= 2:
                    pos = v.gstin[:2]
                elif v.state_type == 'within':
                    pos = '29'
                elif v.state_type == 'other':
                    pos = '27'
                total_invoice_value = sum((item.invoice_value or Decimal('0') for item in v.items.all()))
                if total_invoice_value > 0:
                    advance_amount = Decimal(str(pay.payment_advance))
                    rate_groups = {}
                    for item in v.items.all():
                        inv_val = item.invoice_value or Decimal('0')
                        if inv_val <= 0:
                            continue
                        taxable = item.taxable_value or Decimal('0')
                        igst = item.igst or Decimal('0')
                        cgst = item.cgst or Decimal('0')
                        sgst = item.sgst or Decimal('0')
                        cess = item.cess or Decimal('0')
                        total_tax = igst + cgst + sgst
                        implied_rate = Decimal('0')
                        if taxable > 0:
                            implied_rate = round(total_tax / taxable * 100)
                        rate = float(implied_rate)
                        if rate not in rate_groups:
                            rate_groups[rate] = {'invoice_value': Decimal('0'), 'cess': Decimal('0')}
                        rate_groups[rate]['invoice_value'] += inv_val
                        rate_groups[rate]['cess'] += cess
                    for rate, totals in rate_groups.items():
                        proportion = totals['invoice_value'] / total_invoice_value
                        apportioned_advance = advance_amount * proportion
                        apportioned_cess = totals['cess'] * (apportioned_advance / totals['invoice_value']) if totals['invoice_value'] > 0 else Decimal('0')
                        data.append({'voucher_id': v.id, 'voucher_no': v.sales_invoice_no, 'place_of_supply': pos, 'rate': rate, 'gross_advance_received': float(round(apportioned_advance, 2)), 'cess_amount': float(round(apportioned_cess, 2))})
                else:
                    data.append({'voucher_id': v.id, 'voucher_no': v.sales_invoice_no, 'place_of_supply': pos, 'rate': 0, 'gross_advance_received': float(pay.payment_advance), 'cess_amount': 0})
        return Response(data)

    @action(detail=False, methods=['get'])
    def atadja(self, request):
        """
        Get ATADJA - Amended Advance Tax Adjustment
        Query amended vouchers where advance was used/adjusted and apportion across tax rates.
        """
        from decimal import Decimal
        queryset = self.get_queryset().exclude(amendment_date__isnull=True)
        data = []
        for v in queryset:
            snap = v.original_voucher_snapshot or {}
            pay = get_payment_details(v)
            orig_pay = snap.get('payment_details', {})
            orig_advance = Decimal(str(orig_pay.get('payment_advance', 0))) if orig_pay else Decimal('0')
            amended_advance = Decimal(str(pay.payment_advance)) if pay and pay.payment_advance else Decimal('0')
            if orig_advance <= 0 and amended_advance <= 0:
                continue
            orig_gstin = snap.get('gstin', v.gstin) or ''
            orig_pos = ''
            snap_pos = snap.get('place_of_supply', '') or ''
            STATE_TO_CODE = {'jammu and kashmir': '01', 'himachal pradesh': '02', 'punjab': '03', 'chandigarh': '04', 'uttarakhand': '05', 'haryana': '06', 'delhi': '07', 'rajasthan': '08', 'uttar pradesh': '09', 'bihar': '10', 'sikkim': '11', 'arunachal pradesh': '12', 'nagaland': '13', 'manipur': '14', 'mizoram': '15', 'tripura': '16', 'meghalaya': '17', 'assam': '18', 'west bengal': '19', 'jharkhand': '20', 'odisha': '21', 'chhattisgarh': '22', 'madhya pradesh': '23', 'gujarat': '24', 'daman and diu': '25', 'dadra and nagar haveli': '26', 'maharashtra': '27', 'andhra pradesh (old)': '28', 'karnataka': '29', 'goa': '30', 'lakshadweep': '31', 'kerala': '32', 'tamil nadu': '33', 'puducherry': '34', 'andaman and nicobar islands': '35', 'telangana': '36', 'andhra pradesh': '37', 'ladakh': '38', 'other territory': '97'}
            if snap_pos:
                lower_pos = snap_pos.strip().lower()
                if lower_pos.isdigit():
                    orig_pos = lower_pos.zfill(2)
                else:
                    orig_pos = STATE_TO_CODE.get(lower_pos, '')
            if not orig_pos and orig_gstin and (len(orig_gstin) >= 2) and orig_gstin[:2].isdigit():
                orig_pos = orig_gstin[:2]
            if not orig_pos:
                st = snap.get('state_type', v.state_type) or v.state_type or ''
                orig_pos = '33' if st == 'within' else '27' if st == 'other' else '33'
            months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            orig_month = months[v.date.month - 1] if v.date else 'June'
            total_invoice_value = sum((item.invoice_value or Decimal('0') for item in v.items.all()))
            if total_invoice_value > 0 and amended_advance > 0:
                rate_groups = {}
                for item in v.items.all():
                    inv_val = item.invoice_value or Decimal('0')
                    if inv_val <= 0:
                        continue
                    taxable = item.taxable_value or Decimal('0')
                    total_tax = (item.igst or Decimal('0')) + (item.cgst or Decimal('0')) + (item.sgst or Decimal('0'))
                    cess = item.cess or Decimal('0')
                    implied_rate = round(total_tax / taxable * 100) if taxable > 0 else Decimal('0')
                    rate = float(implied_rate)
                    if rate not in rate_groups:
                        rate_groups[rate] = {'invoice_value': Decimal('0'), 'cess': Decimal('0')}
                    rate_groups[rate]['invoice_value'] += inv_val
                    rate_groups[rate]['cess'] += cess
                for rate, totals in rate_groups.items():
                    proportion = totals['invoice_value'] / total_invoice_value
                    apportioned_amended = amended_advance * proportion
                    apportioned_cess = totals['cess'] * (apportioned_amended / totals['invoice_value']) if totals['invoice_value'] > 0 else Decimal('0')
                    data.append({'voucher_id': v.id, 'voucher_no': v.sales_invoice_no, 'original_month': orig_month, 'original_place_of_supply': orig_pos, 'rate': rate, 'gross_advance_adjusted': float(round(apportioned_amended, 2)), 'cess_amount': float(round(apportioned_cess, 2))})
            else:
                data.append({'voucher_id': v.id, 'voucher_no': v.sales_invoice_no, 'original_month': orig_month, 'original_place_of_supply': orig_pos, 'rate': 0, 'gross_advance_adjusted': float(round(amended_advance, 2)), 'cess_amount': 0})
        return Response(data)

    @action(detail=False, methods=['get'])
    def exemp(self, request):
        """Get EXEMP - Exempted Supplies"""
        queryset = self.get_queryset()
        items = VoucherSalesItems.objects.filter(invoice__in=queryset).select_related('invoice')
        from core.models import Branch
        tenant_ids = list(queryset.values_list('tenant_id', flat=True).distinct())
        branch_map = {b.id: b.state for b in Branch.objects.filter(id__in=tenant_ids)}
        state_name_to_code = {'jammu and kashmir': '01', 'jammu & kashmir': '01', 'j&k': '01', 'himachal pradesh': '02', 'punjab': '03', 'chandigarh': '04', 'uttarakhand': '05', 'uttaranchal': '05', 'haryana': '06', 'delhi': '07', 'rajasthan': '08', 'uttar pradesh': '09', 'up': '09', 'bihar': '10', 'sikkim': '11', 'arunachal pradesh': '12', 'nagaland': '13', 'manipur': '14', 'mizoram': '15', 'tripura': '16', 'meghalaya': '17', 'assam': '18', 'west bengal': '19', 'wb': '19', 'jharkhand': '20', 'odisha': '21', 'orissa': '21', 'chhattisgarh': '22', 'madhya pradesh': '23', 'mp': '23', 'gujarat': '24', 'daman and diu': '25', 'daman & diu': '25', 'dadra and nagar haveli': '26', 'dadra & nagar haveli': '26', 'maharashtra': '27', 'andhra pradesh (old)': '28', 'karnataka': '29', 'goa': '30', 'lakshadweep': '31', 'kerala': '32', 'tamil nadu': '33', 'tamilnadu': '33', 'tn': '33', 'puducherry': '34', 'pondicherry': '34', 'andaman and nicobar islands': '35', 'andaman & nicobar islands': '35', 'telangana': '36', 'andhra pradesh': '37', 'ap': '37', 'ladakh': '38'}
        results_map = {'Inter-State supplies to registered persons': {'description': 'Inter-State supplies to registered persons', 'nil_rated_supplies': 0.0, 'exempted': 0.0, 'non_gst_supplies': 0.0, 'vouchers': {}}, 'Intra-State supplies to registered persons': {'description': 'Intra-State supplies to registered persons', 'nil_rated_supplies': 0.0, 'exempted': 0.0, 'non_gst_supplies': 0.0, 'vouchers': {}}, 'Inter-State supplies to unregistered persons': {'description': 'Inter-State supplies to unregistered persons', 'nil_rated_supplies': 0.0, 'exempted': 0.0, 'non_gst_supplies': 0.0, 'vouchers': {}}, 'Intra-State supplies to unregistered persons': {'description': 'Intra-State supplies to unregistered persons', 'nil_rated_supplies': 0.0, 'exempted': 0.0, 'non_gst_supplies': 0.0, 'vouchers': {}}}
        for item in items:
            igst = float(item.igst or 0)
            cgst = float(item.cgst or 0)
            sgst = float(item.sgst or 0)
            cess = float(item.cess or 0)
            if igst + cgst + sgst + cess > 0:
                continue
            taxable_val = float(item.taxable_value or 0)
            if taxable_val == 0:
                continue
            ledger = str(item.sales_ledger or '').lower()
            if 'non-gst' in ledger or 'non gst' in ledger:
                e_type = 'non_gst_supplies'
            elif 'exempt' in ledger:
                e_type = 'exempted'
            else:
                e_type = 'nil_rated_supplies'
            inv = item.invoice
            gstin = str(inv.gstin or '').strip()
            is_registered = bool(gstin and gstin.lower() != 'unregistered')
            is_inter = inv.state_type == 'other'
            if inv.place_of_supply:
                branch_state = branch_map.get(inv.tenant_id)
                if branch_state:
                    company_code = state_name_to_code.get(str(branch_state).strip().lower())
                    pos_code = str(inv.place_of_supply).zfill(2)
                    if company_code:
                        is_inter = pos_code != company_code
            if is_inter and is_registered:
                desc = 'Inter-State supplies to registered persons'
            elif not is_inter and is_registered:
                desc = 'Intra-State supplies to registered persons'
            elif is_inter and (not is_registered):
                desc = 'Inter-State supplies to unregistered persons'
            else:
                desc = 'Intra-State supplies to unregistered persons'
            results_map[desc][e_type] += taxable_val
            v_id = inv.id
            if v_id not in results_map[desc]['vouchers']:
                results_map[desc]['vouchers'][v_id] = {'voucher_id': v_id, 'voucher_no': inv.sales_invoice_no, 'date': str(inv.date), 'customer_name': inv.customer_name, 'total_taxable_value': 0.0}
            results_map[desc]['vouchers'][v_id]['total_taxable_value'] += taxable_val
        final_list = []
        for v in results_map.values():
            v['nil_rated_supplies'] = round(v['nil_rated_supplies'], 2)
            v['exempted'] = round(v['exempted'], 2)
            v['non_gst_supplies'] = round(v['non_gst_supplies'], 2)
            v['vouchers'] = list(v['vouchers'].values())
            for vouch in v['vouchers']:
                vouch['total_taxable_value'] = round(vouch['total_taxable_value'], 2)
            final_list.append(v)
        return Response(final_list)

    @action(detail=False, methods=['get'])
    def doc(self, request):
        """
        Get DOC - Document Details
        From VoucherSalesInvoiceDetails
        Includes cancelled invoices in the sequence range but counts them separately.
        """
        all_qs = self.get_queryset(include_cancelled=True)
        inv_count = all_qs.count()
        min_no = all_qs.aggregate(Min('sales_invoice_no'))['sales_invoice_no__min']
        max_no = all_qs.aggregate(Max('sales_invoice_no'))['sales_invoice_no__max']
        cancelled_count = all_qs.filter(status='cancelled').count()
        data = []
        if inv_count > 0:
            data.append({'nature_of_document': 'Invoices for outward supply', 'sr_no_from': min_no, 'sr_no_to': max_no, 'total_number': inv_count, 'cancelled': cancelled_count})
        return Response(data)

    @action(detail=False, methods=['get'])
    def doc_details(self, request):
        """
        Returns the detailed list of all invoices (including cancelled) for the DOC drill-down.
        """
        all_qs = self.get_queryset(include_cancelled=True).order_by('date', 'sales_invoice_no')
        data = []
        for inv in all_qs:
            data.append({'id': inv.id, 'invoice_no': inv.sales_invoice_no, 'invoice_date': str(inv.date), 'customer_name': inv.customer_name, 'status': inv.status})
        return Response(data)

    def _get_hsn_pandas(self, queryset, is_b2b):
        """
        Helper to calculate HSN summary using Pandas.
        Avoids Django ORM aggregation errors.
        """
        items_qs = VoucherSalesItems.objects.filter(invoice__in=queryset).values('hsn_sac', 'uom', 'item_rate', 'qty', 'invoice_value', 'taxable_value', 'igst', 'cgst', 'sgst', 'cess', 'invoice__gstin')
        if not items_qs.exists():
            return []
        df = pd.DataFrame(items_qs)
        numeric_cols = ['qty', 'invoice_value', 'taxable_value', 'igst', 'cgst', 'sgst', 'cess']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['is_b2b'] = df['invoice__gstin'].apply(lambda x: True if x and str(x).strip() and (str(x).lower() != 'unregistered') else False)
        if is_b2b:
            df_filtered = df[df['is_b2b']]
        else:
            df_filtered = df[~df['is_b2b']]
        if df_filtered.empty:
            return []
        grouped = df_filtered.groupby(['hsn_sac', 'uom', 'item_rate'], as_index=False).sum()
        return [{'hsn': row['hsn_sac'], 'description': '', 'uqc': row['uom'], 'total_quantity': row['qty'], 'total_value': row['invoice_value'], 'rate': row['item_rate'], 'taxable_value': row['taxable_value'], 'integrated_tax_amount': row['igst'], 'central_tax_amount': row['cgst'], 'state_ut_tax_amount': row['sgst'], 'cess_amount': row['cess']} for _, row in grouped.iterrows()]

    @action(detail=False, methods=['get'])
    def hsnb2b(self, request):
        """Get HSN Summary B2B"""
        data = self._get_hsn_pandas(self.get_queryset(), is_b2b=True)
        return Response(data)

    @action(detail=False, methods=['get'])
    def hsnb2c(self, request):
        """Get HSN Summary B2C"""
        data = self._get_hsn_pandas(self.get_queryset(), is_b2b=False)
        return Response(data)

    @action(detail=False, methods=['get'])
    def hsn_invoices(self, request):
        """Get list of invoices for a specific HSN drilldown"""
        hsn_code = request.query_params.get('hsn_code')
        rate = request.query_params.get('rate')
        is_b2b_param = request.query_params.get('is_b2b', 'true').lower() == 'true'
        if not hsn_code or rate is None:
            return Response({'error': 'hsn_code and rate are required'}, status=400)
        try:
            rate = float(rate)
        except ValueError:
            return Response({'error': 'Invalid rate'}, status=400)
        queryset = self.get_queryset()
        items_qs = VoucherSalesItems.objects.filter(invoice__in=queryset, hsn_sac=hsn_code, item_rate=rate).select_related('invoice')
        data = []
        for item in items_qs:
            inv = item.invoice
            has_gstin = bool(inv.gstin and inv.gstin.strip() and (inv.gstin.strip().lower() != 'unregistered'))
            if is_b2b_param and (not has_gstin):
                continue
            if not is_b2b_param and has_gstin:
                continue
            data.append({'id': inv.id, 'reference_id': inv.id, 'voucher_pk': str(inv.voucher_id) if inv.voucher_id else None, 'invoice_no': inv.sales_invoice_no, 'invoice_date': inv.date, 'customer_name': inv.customer_name, 'gstin': inv.gstin if has_gstin else 'Unregistered', 'hsn': item.hsn_sac, 'rate': item.item_rate, 'qty': item.qty, 'uom': item.uom, 'taxable_value': item.taxable_value, 'igst': item.igst, 'cgst': item.cgst, 'sgst': item.sgst, 'cess': item.cess, 'total_value': item.invoice_value})
        return Response(data)

    @action(detail=False, methods=['get'])
    def download_excel(self, request):
        try:
            queryset = self.get_queryset()

            def get_data(method):
                response = method(request)
                if hasattr(response, 'data'):
                    return response.data
                return []
            b2b_rows = get_data(self.b2b)
            b2b_data = pd.DataFrame(b2b_rows)
            if not b2b_data.empty:
                b2b_data = b2b_data.rename(columns={'gstin': 'GSTIN', 'recipient_name': 'Recipient Name', 'invoice_no': 'Invoice No', 'invoice_date': 'Invoice Date', 'invoice_value': 'Invoice Value', 'place_of_supply': 'Place of Supply', 'reverse_charge': 'Rev. Charge', 'taxable_value': 'Taxable Value', 'igst': 'IGST', 'cgst': 'CGST', 'sgst': 'SGST'})
            b2cl_rows = get_data(self.b2cl)
            b2cl_data = pd.DataFrame(b2cl_rows)
            if not b2cl_data.empty:
                b2cl_data = b2cl_data.rename(columns={'invoice_no': 'Invoice No', 'invoice_date': 'Invoice Date', 'invoice_value': 'Invoice Value', 'place_of_supply': 'Place of Supply', 'rate': 'Rate', 'taxable_value': 'Taxable Value', 'igst': 'IGST'})
            b2cs_rows = get_data(self.b2cs)
            b2cs_data = pd.DataFrame(b2cs_rows)
            if not b2cs_data.empty:
                b2cs_data = b2cs_data.rename(columns={'type': 'Type', 'Type': 'Type', 'place_of_supply': 'Place of Supply', 'Place of Supply': 'Place of Supply', 'rate': 'Rate', 'taxable_value': 'Taxable Value', 'igst': 'IGST', 'cgst': 'CGST', 'sgst': 'SGST'})
            exp_rows = get_data(self.exp)
            exp_data = pd.DataFrame(exp_rows)
            if not exp_data.empty:
                exp_data = exp_data.rename(columns={'export_type': 'Export Type', 'invoice_no': 'Invoice No', 'invoice_date': 'Invoice Date', 'invoice_value': 'Invoice Value', 'port_code': 'Port Code', 'shipping_bill_number': 'SB No', 'shipping_bill_date': 'SB Date', 'item_rate': 'Rate', 'taxable_value': 'Taxable Value'})
            atadj_rows = get_data(self.atadj)
            atadj_data = pd.DataFrame(atadj_rows)
            if not atadj_data.empty:
                atadj_data = atadj_data.rename(columns={'place_of_supply': 'Place of Supply(POS)*', 'rate': 'Rate*', 'gross_advance_received': 'Gross advance received*', 'cess': 'Cess Amount'})
            ata_rows = get_data(self.ata)
            ata_data = pd.DataFrame(ata_rows)
            if not ata_data.empty:
                ata_data = ata_data.rename(columns={'original_year': 'Financial Year', 'original_month': 'Original Month*', 'original_pos': 'Original Place of Supply(POS)*', 'revised_rate': 'Rate*', 'revised_amount': 'Gross advance received*', 'cess_amount': 'Cess Amount'})
            doc_rows = get_data(self.doc)
            doc_data = pd.DataFrame(doc_rows)
            if not doc_data.empty:
                doc_data = doc_data.rename(columns={'nature_of_document': 'Nature of Document*', 'sr_no_from': 'Sr. No From*', 'sr_no_to': 'Sr. No To*', 'total_number': 'Total Number*', 'cancelled': 'Cancelled'})
            eco_rows = get_data(self.eco)
            eco_data = pd.DataFrame(eco_rows)
            if not eco_data.empty:
                eco_data = eco_data.rename(columns={'nature_of_supply': 'Nature of Supply*', 'place_of_supply': 'Place of Supply(POS)/ GSTIN*', 'ecommerce_name': 'E-Commerce Operator Name', 'net_value': 'Net value of supplies*', 'igst': 'Integrated Tax Amount', 'cgst': 'Central Tax Amount', 'sgst': 'State/UT Tax Amount', 'cess': 'Cess Amount'})
            ecob2b_rows = get_data(self.ecob2b)
            ecob2b_data = pd.DataFrame(ecob2b_rows)
            if not ecob2b_data.empty:
                ecob2b_data = ecob2b_data.rename(columns={'supplier_gstin': 'GSTIN/UIN of Supplier', 'recipient_gstin': 'GSTIN/UIN of Recipient', 'recipient_name': 'Recipient Name', 'invoice_no': 'Invoice Number', 'invoice_date': 'Document date', 'invoice_value': 'Value of supplies made', 'place_of_supply': 'Place of Supply*', 'supply_type': 'Supply Type*', 'document_type': 'Document type', 'rate': 'Rate*', 'taxable_value': 'Taxable value*', 'cess': 'Cess Amount'})
            ecob2c_rows = get_data(self.ecob2c)
            ecob2c_data = pd.DataFrame(ecob2c_rows)
            if not ecob2c_data.empty:
                ecob2c_data = ecob2c_data.rename(columns={'supplier_gstin': 'GSTIN/UIN of Supplier', 'supplier_name': 'Supplier Name', 'place_of_supply': 'Place of Supply*', 'rate': 'Rate*', 'taxable_value': 'Taxable Value*', 'cess': 'Cess Amount'})
            items_qs = VoucherSalesItems.objects.filter(invoice__in=queryset).values('hsn_sac', 'uom', 'item_rate', 'qty', 'invoice_value', 'taxable_value', 'igst', 'cgst', 'sgst', 'cess', 'invoice__gstin')
            hsn_b2b_rows = []
            hsn_b2c_rows = []
            hsn_b2b_data = pd.DataFrame()
            hsn_b2c_data = pd.DataFrame()
            if items_qs.exists():
                df_hsn = pd.DataFrame(items_qs)
                numeric_cols = ['qty', 'invoice_value', 'taxable_value', 'igst', 'cgst', 'sgst', 'cess']
                for col in numeric_cols:
                    df_hsn[col] = pd.to_numeric(df_hsn[col], errors='coerce').fillna(0)
                df_hsn['is_b2b'] = df_hsn['invoice__gstin'].apply(lambda x: True if x and str(x).strip() and (str(x).lower() != 'unregistered') else False)
                df_b2b = df_hsn[df_hsn['is_b2b']]
                df_b2c = df_hsn[~df_hsn['is_b2b']]

                def aggregate_hsn(df, target_list):
                    if df.empty:
                        return
                    grouped = df.groupby(['hsn_sac', 'uom', 'item_rate'], as_index=False).sum()
                    for _, row in grouped.iterrows():
                        target_list.append({'HSN*': row['hsn_sac'], 'Description': '', 'UQC*': row['uom'], 'Total Quantity*': row['qty'], 'Total Value': row['invoice_value'], 'Rate': row['item_rate'], 'Taxable Value*': row['taxable_value'], 'Integrated Tax Amount': row['igst'], 'Central Tax Amount': row['cgst'], 'State/UT Tax Amount': row['sgst'], 'Cess Amount': row['cess']})
                aggregate_hsn(df_b2b, hsn_b2b_rows)
                aggregate_hsn(df_b2c, hsn_b2c_rows)
            hsn_b2b_data = pd.DataFrame(hsn_b2b_rows)
            hsn_b2c_data = pd.DataFrame(hsn_b2c_rows)
            cols_b2b = ['GSTIN', 'Recipient Name', 'Invoice No', 'Invoice Date', 'Invoice Value', 'Place of Supply', 'Rev. Charge', 'Taxable Value', 'IGST', 'CGST', 'SGST']
            cols_b2cl = ['Invoice No', 'Invoice Date', 'Invoice Value', 'Place of Supply', 'Rate', 'Taxable Value', 'IGST']
            cols_b2cs = ['Type', 'Place of Supply', 'Rate', 'Taxable Value', 'IGST', 'CGST', 'SGST']
            cols_exp = ['Export Type', 'Invoice No', 'Invoice Date', 'Invoice Value', 'Port Code', 'SB No', 'SB Date', 'Rate', 'Taxable Value']
            cols_cdnr = ['GSTIN/UIN*', 'Name of Recipient', 'Note Number*', 'Note date*', 'Note Type*', 'Place of Supply*', 'Reverse charge*', 'Note Supply Type*', 'Note value*', 'Applicable % of Tax Rate', 'Rate*', 'Taxable value*', 'Cess Amount']
            cols_cdnur = ['UR Type*', 'Note Number*', 'Note date*', 'Note Type*', 'Place of Supply', 'Note value*', 'Applicable % of Tax Rate', 'Rate*', 'Taxable value', 'Cess Amount']
            cols_at = ['Place of Supply(POS)*', 'Rate*', 'Gross advance received*', 'Cess Amount']
            cols_atadj = ['Place of Supply(POS)*', 'Rate*', 'Gross advance received*', 'Cess Amount']
            cols_exemp = ['Description', 'Nil rated supplies', 'Exempted', 'Non GST Supplies']
            cols_doc = ['Nature of Document*', 'Sr. No From*', 'Sr. No To*', 'Total Number*', 'Cancelled']
            cols_hsn = ['HSN*', 'Description', 'UQC*', 'Total Quantity*', 'Total Value', 'Rate', 'Taxable Value*', 'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount']
            cols_b2ba = ['GSTIN/UIN of Recipient*', 'Name of Recipient', 'Original Invoice number*', 'Original Invoice Date*', 'Revised Invoice number*', 'Revised Invoice Date*', 'Invoice value*', 'Place of Supply(POS)*', 'Reverse Charge*', 'Applicable % of Tax Rate', 'Invoice Type*', 'E-Commerce GSTIN*', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_b2cla = ['Original Invoice number', 'Original Invoice Date', 'Revised Invoice number*', 'Revised Invoice Date', 'Invoice value*', 'Original Place of Supply(POS)', 'Applicable % of Tax Rate', 'Rate*', 'Taxable Value*', 'Cess Amount', 'E-Commerce GSTIN']
            cols_b2csa = ['Type*', 'Financial Year', 'Original Month', 'Original Place of Supply(POS)', 'Revised Place of Supply(POS)', 'Applicable % of Tax Rate', 'Original Rate*', 'Taxable Value*', 'Cess Amount', 'E-Commerce GSTIN']
            cols_expa = ['Export Type*', 'Original Invoice number*', 'Original Invoice Date*', 'Revised Invoice number*', 'Revised Invoice Date*', 'Invoice value*', 'Port Code', 'Shipping Bill Number', 'Shipping Bill Date', 'Applicable % of Tax Rate', 'Rate', 'Taxable Value']
            cols_cdnra = ['GSTIN/UIN*', 'Name of Recipient', 'Original Note Number*', 'Original Note date*', 'Revised Note Number*', 'Revised Note date*', 'Note Type*', 'Place of Supply*', 'Reverse charge*', 'Note Supply Type*', 'Note value*', 'Applicable % of Tax Rate', 'Rate*', 'Taxable value*', 'Cess Amount']
            cols_ata = ['Financial Year', 'Original Month*', 'Original Place of Supply(POS)*', 'Applicable % of Tax Rate', 'Rate*', 'Gross advance received*', 'Cess Amount']
            cols_atadja = ['Financial Year', 'Original Month*', 'Original Place of Supply(POS)*', 'Applicable % of Tax Rate', 'Rate*', 'Gross advance adjusted*', 'Cess Amount']
            cols_eco = ['Nature of Supply*', 'Place of Supply(POS)/ GSTIN*', 'E-Commerce Operator Name', 'Net value of supplies*', 'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount']
            cols_ecoa = ['Nature of Supply*', 'Original Month*', 'E-Commerce Operator GSTIN*', 'E-Commerce Operator Name', 'Net value of supplies*', 'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount', 'Financial Year']
            cols_ecob2b = ['GSTIN/UIN of Supplier', 'GSTIN/UIN of Recipient', 'Recipient Name', 'Invoice Number', 'Document date', 'Value of supplies made', 'Place of Supply*', 'Supply Type*', 'Document type', 'Rate*', 'Taxable value*', 'Cess Amount']
            cols_ecourp2b = ['GSTIN/UIN of Recipient', 'Recipient Name', 'Document Number', 'Document Date', 'Value of Supplies Made', 'Place of Supply', 'Document Type', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecob2c = ['GSTIN/UIN of Supplier', 'Supplier Name', 'Place of Supply*', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecourp2c = ['Place of Supply*', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecoab2b = ['GSTIN/UIN of Supplier', 'Supplier Name', 'GSTIN/UIN of Recipient', 'Recipient Name', 'Original Document Number', 'Original Document Date', 'Revised Document Number', 'Revised Document Date', 'Value of Supplies Made', 'Place of Supply', 'Document Type', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecoab2c = ['Financial Year*', 'Original Month*', 'GSTIN/UIN of Supplier', 'Supplier Name', 'Place of Supply*', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecoaurp2b = ['GSTIN/UIN of Recipient', 'Recipient Name', 'Original Document Number', 'Original Document Date', 'Revised Document Number', 'Revised Document Date', 'Value of Supplies Made', 'Place of Supply', 'Document Type', 'Rate*', 'Taxable Value*', 'Cess Amount']
            cols_ecoaurp2c = ['Financial Year*', 'Original Month*', 'Place Of Supply', 'Rate*', 'Taxable Value*', 'Cess Amount']

            def get_df(rows, cols):
                if isinstance(rows, pd.DataFrame):
                    df = rows
                elif rows:
                    df = pd.DataFrame(rows)
                else:
                    return pd.DataFrame(columns=cols)
                for c in cols:
                    if c not in df.columns:
                        df[c] = ''
                return df[cols]
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                get_df(b2b_data if not b2b_data.empty else [], cols_b2b).to_excel(writer, sheet_name='B2B', index=False)
                get_df(b2cl_data if not b2cl_data.empty else [], cols_b2cl).to_excel(writer, sheet_name='B2CL', index=False)
                get_df(b2cs_data if not b2cs_data.empty else [], cols_b2cs).to_excel(writer, sheet_name='B2CS', index=False)
                get_df(exp_data if not exp_data.empty else [], cols_exp).to_excel(writer, sheet_name='EXP', index=False)
                get_df([], cols_cdnr).to_excel(writer, sheet_name='CDNR', index=False)
                get_df([], cols_cdnur).to_excel(writer, sheet_name='CDNUR', index=False)
                get_df([], cols_at).to_excel(writer, sheet_name='AT', index=False)
                get_df(atadj_data if not atadj_data.empty else [], cols_atadj).to_excel(writer, sheet_name='ATADJ', index=False)
                get_df([], cols_exemp).to_excel(writer, sheet_name='EXEMP', index=False)
                get_df(hsn_b2b_data if not hsn_b2b_data.empty else [], cols_hsn).to_excel(writer, sheet_name='HSNB2B', index=False)
                get_df(hsn_b2c_data if not hsn_b2c_data.empty else [], cols_hsn).to_excel(writer, sheet_name='HSNB2C', index=False)
                get_df(doc_data if not doc_data.empty else [], cols_doc).to_excel(writer, sheet_name='DOC', index=False)
                get_df([], cols_b2ba).to_excel(writer, sheet_name='B2BA', index=False)
                get_df([], cols_b2cla).to_excel(writer, sheet_name='B2CLA', index=False)
                get_df([], cols_b2csa).to_excel(writer, sheet_name='B2CSA', index=False)
                get_df([], cols_expa).to_excel(writer, sheet_name='EXPA', index=False)
                get_df(cdnra_data if 'cdnra_data' in locals() and (not cdnra_data.empty) else [], cols_cdnra).to_excel(writer, sheet_name='CDNRA', index=False)
                get_df(ata_data if 'ata_data' in locals() and (not ata_data.empty) else [], cols_ata).to_excel(writer, sheet_name='ATA', index=False)
                get_df([], cols_atadja).to_excel(writer, sheet_name='ATADJA', index=False)
                get_df(eco_data if not eco_data.empty else [], cols_eco).to_excel(writer, sheet_name='ECO', index=False)
                get_df([], cols_ecoa).to_excel(writer, sheet_name='ECOA', index=False)
                get_df(ecob2b_data if not ecob2b_data.empty else [], cols_ecob2b).to_excel(writer, sheet_name='ECOB2B', index=False)
                get_df([], cols_ecourp2b).to_excel(writer, sheet_name='ECOURP2B', index=False)
                get_df(ecob2c_data if not ecob2c_data.empty else [], cols_ecob2c).to_excel(writer, sheet_name='ECOB2C', index=False)
                get_df([], cols_ecourp2c).to_excel(writer, sheet_name='ECOURP2C', index=False)
                get_df([], cols_ecoab2b).to_excel(writer, sheet_name='ECOAB2B', index=False)
                get_df([], cols_ecoab2c).to_excel(writer, sheet_name='ECOAB2C', index=False)
                get_df([], cols_ecoaurp2b).to_excel(writer, sheet_name='ECOAURP2B', index=False)
                get_df([], cols_ecoaurp2c).to_excel(writer, sheet_name='ECOAURP2C', index=False)
            output.seek(0)
            year = request.query_params.get('year', '2024-25')
            month = request.query_params.get('month', 'All')
            filename = f'GSTR1_{year}_{month}.xlsx'
            return FileResponse(output, as_attachment=True, filename=filename, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'])
    def download_json(self, request):
        queryset = self.get_queryset()
        year_str = request.query_params.get('year', '2024-25')
        month_name = request.query_params.get('month', 'January')
        months_map = {'January': '01', 'February': '02', 'March': '03', 'April': '04', 'May': '05', 'June': '06', 'July': '07', 'August': '08', 'September': '09', 'October': '10', 'November': '11', 'December': '12'}
        month_num = months_map.get(month_name, '01')
        actual_year = year_str.split('-')[0]
        if month_name in {'January', 'February', 'March'}:
            try:
                actual_year = str(int(actual_year) + 1)
            except:
                pass
        data = {'gstin': 'UNAVAILABLE', 'fp': f'{month_num}{actual_year}', 'b2b': [], 'b2cl': []}
        for v in queryset:
            pay = get_payment_details(v)
            val = pay.payment_invoice_value if pay else 0
            taxable = pay.payment_taxable_value if pay else 0
            igst = pay.payment_igst if pay else 0
            cgst = pay.payment_cgst if pay else 0
            sgst = pay.payment_sgst if pay else 0
            has_gstin = v.gstin and v.gstin.strip()
            is_large = val > 250000
            is_inter = v.state_type == 'other'
            pos = ''
            if has_gstin and len(v.gstin) >= 2:
                pos = v.gstin[:2]
            elif v.state_type == 'within':
                pos = '29'
            elif v.state_type == 'other':
                pos = '27'
            item = {'inum': v.sales_invoice_no, 'idt': str(v.date), 'val': float(val), 'pos': pos, 'rchrg': 'N', 'inv_typ': 'R', 'itms': [{'num': 1, 'itm_det': {'txval': float(taxable), 'rt': 0, 'iamt': float(igst), 'camt': float(cgst), 'samt': float(sgst), 'csamt': 0}}]}
            if has_gstin:
                ctin = v.gstin
                found = False
                for entry in data['b2b']:
                    if entry['ctin'] == ctin:
                        entry['inv'].append(item)
                        found = True
                        break
                if not found:
                    data['b2b'].append({'ctin': ctin, 'inv': [item]})
            elif not has_gstin and is_large and is_inter:
                found = False
                for entry in data['b2cl']:
                    if entry['pos'] == pos:
                        entry['inv'].append(item)
                        found = True
                        break
                if not found:
                    data['b2cl'].append({'pos': v.place_of_supply, 'inv': [item]})
        filename = f'GSTR1_{year_str}_{month_name}.json'
        response = HttpResponse(json.dumps(data, default=str), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'])
    def file_return(self, request):
        """
        Mark all sales vouchers in a given month/year as GST-filed (gst_registered=True).
        
        Restrictions:
        - Cannot file for the current month (only previous months allowed).
        - Returns count of vouchers updated.
        """
        from django.utils import timezone
        year_str = request.data.get('year')
        month_str = request.data.get('month')
        if not year_str or not month_str:
            return Response({'error': 'year and month are required.'}, status=status.HTTP_400_BAD_REQUEST)
        months_map = {'April': (4, 0), 'May': (5, 0), 'June': (6, 0), 'July': (7, 0), 'August': (8, 0), 'September': (9, 0), 'October': (10, 0), 'November': (11, 0), 'December': (12, 0), 'January': (1, 1), 'February': (2, 1), 'March': (3, 1)}
        try:
            start_year = int(year_str.split('-')[0])
        except Exception:
            return Response({'error': 'Invalid year format. Use e.g. 2025-26.'}, status=status.HTTP_400_BAD_REQUEST)
        month_info = months_map.get(month_str)
        if not month_info:
            return Response({'error': f'Invalid month: {month_str}.'}, status=status.HTTP_400_BAD_REQUEST)
        month_num, year_offset = month_info
        filter_year = start_year + year_offset
        today = timezone.now().date()
        if filter_year == today.year and month_num == today.month:
            return Response({'error': 'GST return cannot be filed for the current month. Only previous months are allowed.'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        qs = VoucherSalesInvoiceDetails.objects.filter(date__year=filter_year, date__month=month_num, gst_registered='')
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        cn_qs = VoucherCreditNoteInvoiceDetails.objects.filter(date__year=filter_year, date__month=month_num, gst_registered='')
        if tenant_id:
            cn_qs = cn_qs.filter(tenant_id=tenant_id)
        count = qs.count()
        cn_count = cn_qs.count()
        if count == 0 and cn_count == 0:
            return Response({'message': f'No unfiled vouchers found for {month_str} {filter_year}.', 'updated_count': 0})
        if count > 0:
            qs.update(gst_registered='Yes')
        if cn_count > 0:
            cn_qs.update(gst_registered='Yes')
        adv_qs = AdvanceAllocation.objects.filter(transaction__date__year=filter_year, transaction__date__month=month_num, transaction__transaction_type='RECEIPT', gst_registered='')
        if tenant_id:
            adv_qs = adv_qs.filter(tenant_id=tenant_id)
        adv_count = adv_qs.count()
        if adv_count > 0:
            adv_qs.update(gst_registered='Yes')
        return Response({'message': f'Successfully filed GST return for {month_str} {filter_year}.', 'updated_count': count + cn_count + adv_count, 'month': month_str, 'year': year_str, 'filter_year': filter_year, 'month_num': month_num})

    @action(detail=False, methods=['post'])
    def file_amendment(self, request):
        """
        File all pending amendments (EXPA + B2BA) for a given month/year.

        What it does:
        - Finds all sales vouchers in the period that have amendment_date set
          (these are the records showing in EXPA and B2BA tabs).
        - Clears amendment_date and original_voucher_snapshot so they are
          treated as freshly filed and exit the amendment tabs.
        - Updates gst_registered = 'Yes' to confirm they remain GST-filed.

        Restrictions:
        - Cannot file for the current month.
        """
        from django.utils import timezone
        year_str = request.data.get('year')
        month_str = request.data.get('month')
        if not year_str or not month_str:
            return Response({'error': 'year and month are required.'}, status=status.HTTP_400_BAD_REQUEST)
        months_map = {'April': (4, 0), 'May': (5, 0), 'June': (6, 0), 'July': (7, 0), 'August': (8, 0), 'September': (9, 0), 'October': (10, 0), 'November': (11, 0), 'December': (12, 0), 'January': (1, 1), 'February': (2, 1), 'March': (3, 1)}
        try:
            start_year = int(year_str.split('-')[0])
        except Exception:
            return Response({'error': 'Invalid year format. Use e.g. 2025-26.'}, status=status.HTTP_400_BAD_REQUEST)
        month_info = months_map.get(month_str)
        if not month_info:
            return Response({'error': f'Invalid month: {month_str}.'}, status=status.HTTP_400_BAD_REQUEST)
        month_num, year_offset = month_info
        filter_year = start_year + year_offset
        today = timezone.now().date()
        if filter_year == today.year and month_num == today.month:
            return Response({'error': 'Amendment cannot be filed for the current month. Only previous months are allowed.'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None)
        qs = VoucherSalesInvoiceDetails.objects.filter(date__year=filter_year, date__month=month_num).exclude(amendment_date__isnull=True).filter(amendment_filed=False)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails
        cn_qs = VoucherCreditNoteInvoiceDetails.objects.filter(date__year=filter_year, date__month=month_num).exclude(amendment_date__isnull=True).filter(amendment_filed=False)
        if tenant_id:
            cn_qs = cn_qs.filter(tenant_id=tenant_id)
        adv_qs = AdvanceAllocation.objects.filter(transaction__date__year=filter_year, transaction__date__month=month_num, transaction__transaction_type='RECEIPT', gst_registered='Yes', amendment_date__isnull=False, amendment_filed=False)
        if tenant_id:
            adv_qs = adv_qs.filter(tenant_id=tenant_id)
        adv_count = adv_qs.count()
        count = qs.count()
        cn_count = cn_qs.count()
        if count == 0 and cn_count == 0 and (adv_count == 0):
            return Response({'message': f'No pending amendments found for {month_str} {filter_year}.', 'updated_count': 0})
        if count > 0:
            qs.update(amendment_filed=True, gst_registered='Yes')
        if cn_count > 0:
            cn_qs.update(amendment_filed=True, gst_registered='Yes')
        if adv_count > 0:
            adv_qs.update(amendment_filed=True)
        return Response({'message': f'Successfully filed amendments for {month_str} {filter_year}. (Sales: {count}, Credit Notes: {cn_count}, ATA: {adv_count})', 'updated_count': count + cn_count + adv_count, 'month': month_str, 'year': year_str})