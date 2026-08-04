from rest_framework import viewsets, status
from django.db.models import Sum, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from accounting.models_voucher_debit_note import VoucherDebitNoteSupplierDetails
from core.mixins import IsBranchMember

class GSTR2ViewSet(viewsets.ViewSet):
    """
    ViewSet for generating GSTR2 (Purchase Register) data.
    """
    permission_classes = [IsAuthenticated, IsBranchMember]

    def get_purchase_queryset(self):
        user = self.request.user
        tenant_id = getattr(user, 'tenant_id', None)
        if tenant_id:
            queryset = VoucherPurchaseSupplierDetails.objects.filter(tenant_id=tenant_id)
        else:
            queryset = VoucherPurchaseSupplierDetails.objects.all()
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
        return queryset

    def get_debit_note_queryset(self):
        user = self.request.user
        tenant_id = getattr(user, 'tenant_id', None)
        if tenant_id:
            queryset = VoucherDebitNoteSupplierDetails.objects.filter(tenant_id=tenant_id)
        else:
            queryset = VoucherDebitNoteSupplierDetails.objects.all()
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
        return queryset

    @action(detail=False, methods=['get'])
    def b2b(self, request):
        """Get B2B Purchases (Registered Vendors)"""
        vouchers = self.get_purchase_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(input_type__iexact='Import').exclude(invoice_in_foreign_currency='Yes')
        data = []
        for v in vouchers:
            items = v.line_items.all()
            taxable = sum((item.taxable_value for item in items))
            igst = sum((item.igst_amount for item in items))
            cgst = sum((item.cgst_amount for item in items))
            sgst = sum((item.sgst_amount for item in items))
            val = sum((item.invoice_value for item in items))
            pos = ''
            if v.gstin and len(v.gstin) >= 2:
                pos = v.gstin[:2]
            elif v.input_type == 'Intrastate':
                pos = '29'
            elif v.input_type == 'Interstate':
                pos = '27'
            data.append({'id': v.id, 'gstin': v.gstin, 'supplier_name': v.vendor_name, 'invoice_no': v.supplier_invoice_no or v.purchase_voucher_no, 'invoice_date': v.supplier_invoice_date or v.date, 'invoice_value': val, 'place_of_supply': pos, 'reverse_charge': 'N', 'taxable_value': taxable, 'igst': igst, 'cgst': cgst, 'sgst': sgst, 'source': 'b2b_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def b2bur(self, request):
        """Get B2BUR Purchases (Unregistered Vendors)"""
        vouchers = self.get_purchase_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(input_type__iexact='Import').exclude(invoice_in_foreign_currency='Yes')
        data = []
        for v in vouchers:
            items = v.line_items.all()
            taxable = sum((item.taxable_value for item in items))
            igst = sum((item.igst_amount for item in items))
            cgst = sum((item.cgst_amount for item in items))
            sgst = sum((item.sgst_amount for item in items))
            val = sum((item.invoice_value for item in items))
            pos = '29' if v.input_type == 'Intrastate' else '27'
            data.append({'id': v.id, 'supplier_name': v.vendor_name, 'invoice_no': v.supplier_invoice_no or v.purchase_voucher_no, 'invoice_date': v.supplier_invoice_date or v.date, 'invoice_value': val, 'place_of_supply': pos, 'taxable_value': taxable, 'igst': igst, 'cgst': cgst, 'sgst': sgst, 'source': 'b2bur_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def impg(self, request):
        """Get Import of Goods/Services (IMPG / IMPS)"""
        vouchers = self.get_purchase_queryset().filter(Q(input_type__iexact='Import') | Q(invoice_in_foreign_currency='Yes'))
        data = []
        for v in vouchers:
            items = v.line_items.all()
            taxable = sum((item.taxable_value for item in items))
            igst = sum((item.igst_amount for item in items))
            val = sum((item.invoice_value for item in items))
            data.append({'id': v.id, 'supplier_name': v.vendor_name, 'port_code': '', 'boe_no': v.supplier_invoice_no or v.purchase_voucher_no, 'boe_date': v.supplier_invoice_date or v.date, 'boe_value': val, 'taxable_value': taxable, 'igst': igst, 'cess': sum((item.cess_amount for item in items)), 'source': 'impg_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def cdnr(self, request):
        """Get CDNR (Credit/Debit Notes to Registered Vendors)"""
        vouchers = self.get_debit_note_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        data = []
        for v in vouchers:
            try:
                item_details = v.item_details
                taxable = item_details.total_taxable_value
                igst = item_details.total_igst
                cgst = item_details.total_cgst
                sgst = item_details.total_sgst
                val = item_details.total_invoice_value
            except Exception:
                taxable = igst = cgst = sgst = val = 0
            data.append({'id': v.id, 'gstin': v.gstin, 'supplier_name': v.vendor_name, 'note_no': v.debit_note_no, 'note_date': v.date, 'note_type': 'D', 'place_of_supply': v.place_of_supply, 'note_value': val, 'taxable_value': taxable, 'igst': igst, 'cgst': cgst, 'sgst': sgst, 'source': 'cdnr_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def cdnur(self, request):
        """Get CDNUR (Credit/Debit Notes to Unregistered Vendors)"""
        vouchers = self.get_debit_note_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        data = []
        for v in vouchers:
            try:
                item_details = v.item_details
                taxable = item_details.total_taxable_value
                igst = item_details.total_igst
                cgst = item_details.total_cgst
                sgst = item_details.total_sgst
                val = item_details.total_invoice_value
            except Exception:
                taxable = igst = cgst = sgst = val = 0
            data.append({'id': v.id, 'supplier_name': v.vendor_name, 'note_no': v.debit_note_no, 'note_date': v.date, 'note_type': 'D', 'place_of_supply': v.place_of_supply, 'note_value': val, 'taxable_value': taxable, 'igst': igst, 'cgst': cgst, 'sgst': sgst, 'source': 'cdnur_drilldown'})
        return Response(data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get summary stats for all GSTR2 sections"""
        b2b_qs = self.get_purchase_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered').exclude(input_type__iexact='Import')
        b2bur_qs = self.get_purchase_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered')).exclude(input_type__iexact='Import')
        impg_qs = self.get_purchase_queryset().filter(input_type__iexact='Import')
        cdnr_qs = self.get_debit_note_queryset().exclude(gstin__isnull=True).exclude(gstin__exact='').exclude(gstin__iexact='unregistered')
        cdnur_qs = self.get_debit_note_queryset().filter(Q(gstin__isnull=True) | Q(gstin__exact='') | Q(gstin__iexact='unregistered'))
        return Response({'B2B': b2b_qs.count(), 'B2BUR': b2bur_qs.count(), 'IMPG': impg_qs.count(), 'CDNR': cdnr_qs.count(), 'CDNUR': cdnur_qs.count()})