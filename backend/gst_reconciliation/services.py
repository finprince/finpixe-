import re
from decimal import Decimal
from .models import ValidationResult, GSTR3BReport, ITCSummary
from accounting.models_voucher_sales import VoucherSalesInvoiceDetails

class GSTValidationService:

    @staticmethod
    def validate_gstin(gstin):
        """Simple GSTIN pattern check."""
        pattern = '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        return bool(re.match(pattern, gstin))

    @staticmethod
    def run_period_validation(month, year):
        """Module 5: Validation Layer logic."""
        results = []
        from .models import GSTR2BInvoice
        invalid_gstins = GSTR2BInvoice.objects.all().filter(invoice_date__year=2024)
        for inv in invalid_gstins:
            if not GSTValidationService.validate_gstin(inv.gstin):
                results.append(ValidationResult.objects.create(period_month=month, period_year=year, check_type='GSTIN_VALIDATION', message=f"Invalid GSTIN '{inv.gstin}' found in invoice {inv.invoice_no}"))
        report_3b = GSTR3BReport.objects.filter(period_month=month, period_year=year).last()
        if report_3b:
            sales = VoucherSalesInvoiceDetails.objects.all()
            total_sales_igst = sum((float(v.payment_details.payment_igst) for v in sales if hasattr(v, 'payment_details')))
            total_sales_cgst = sum((float(v.payment_details.payment_cgst) for v in sales if hasattr(v, 'payment_details')))
            total_sales_sgst = sum((float(v.payment_details.payment_sgst) for v in sales if hasattr(v, 'payment_details')))
            if abs(total_sales_igst - float(report_3b.output_tax_igst)) > 1:
                results.append(ValidationResult.objects.create(period_month=month, period_year=year, check_type='TAX_MISMATCH', message=f'GSTR-1 Liability (₹{total_sales_igst}) differs from 3B (₹{report_3b.output_tax_igst})'))
        return results