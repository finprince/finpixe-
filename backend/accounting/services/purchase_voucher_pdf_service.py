"""
Purchase Voucher / Invoice PDF Generation Service
-------------------------------------------------
Generates a GST-compliant, executive-grade Purchase Voucher PDF
using ReportLab with precise layout, table formatting, and styling.
"""

import io
import os
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, KeepTogether, HRFlowable
)

logger = logging.getLogger("accounting.purchase_pdf")

# Palette tokens matching executive UI theme
COLOR_PRIMARY = colors.HexColor("#1E3A8A")     # Deep Navy
COLOR_SECONDARY = colors.HexColor("#3B82F6")   # Royal Blue
COLOR_ACCENT = colors.HexColor("#4F46E5")      # Indigo
COLOR_DARK = colors.HexColor("#1E293B")        # Slate 800
COLOR_MUTED = colors.HexColor("#64748B")       # Slate 500
COLOR_LIGHT = colors.HexColor("#F8FAFC")       # Off-white / light slate
COLOR_BORDER = colors.HexColor("#CBD5E1")      # Border grey
COLOR_HEADER_BG = colors.HexColor("#1E3A8A")   # Table header background
COLOR_ZEBRA = colors.HexColor("#F1F5F9")       # Light grey zebra row


def _fmt_curr(val: Any) -> str:
    """Safely format numbers into INR currency string."""
    try:
        num = float(val or 0)
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _num_to_words(amount: float) -> str:
    """Convert numerical amount into Indian currency words."""
    try:
        from num2words import num2words
        words = num2words(amount, lang='en_IN', to='currency', currency='INR')
        return words.replace('rupees', 'Rupees').replace('paise', 'Paise').title()
    except Exception:
        try:
            ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

            def _two_digits(n):
                if n < 20:
                    return ones[n]
                return (tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")).strip()

            def _three_digits(n):
                h = n // 100
                r = n % 100
                res = ""
                if h > 0:
                    res += ones[h] + " Hundred"
                if r > 0:
                    res += (" " if res else "") + _two_digits(r)
                return res

            amt = int(round(amount))
            if amt == 0:
                return "Zero Rupees Only"
            
            crore = amt // 10000000
            amt %= 10000000
            lakh = amt // 100000
            amt %= 100000
            thousand = amt // 1000
            amt %= 1000
            hundred = amt

            parts = []
            if crore > 0:
                parts.append(_three_digits(crore) + " Crore")
            if lakh > 0:
                parts.append(_two_digits(lakh) + " Lakh")
            if thousand > 0:
                parts.append(_two_digits(thousand) + " Thousand")
            if hundred > 0:
                parts.append(_three_digits(hundred))

            return "Rupees " + " ".join(parts) + " Only"
        except Exception:
            return f"Rupees {_fmt_curr(amount)} Only"


def _get_company_info(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve company master profile for headers."""
    info = {
        'name': 'FINPIXE ACCOUNTING',
        'trade_name': 'Finpixe Enterprises',
        'address': 'Registered Office, Corporate Hub',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'pincode': '600001',
        'gstin': '33AAAAA0000A1Z5',
        'pan': 'AAAAA0000A',
        'cin': 'U72900TN2024PTC123456',
        'email': 'accounts@finpixe.com',
        'phone': '+91 98765 43210',
        'bank_name': 'HDFC Bank Ltd.',
        'account_no': '50200012345678',
        'ifsc': 'HDFC0001234',
        'branch_name': 'Main Branch',
    }
    try:
        from core.models import CompanyDetails
        comp = CompanyDetails.objects.filter(is_active=True).first() if not tenant_id else (
            CompanyDetails.objects.filter(tenant_id=tenant_id).first() or CompanyDetails.objects.first()
        )
        if comp:
            info['name'] = getattr(comp, 'company_name', None) or getattr(comp, 'name', None) or info['name']
            info['trade_name'] = getattr(comp, 'trade_name', None) or info['name']
            info['address'] = getattr(comp, 'registered_address', None) or getattr(comp, 'address', None) or info['address']
            info['city'] = getattr(comp, 'city', None) or info['city']
            info['state'] = getattr(comp, 'state', None) or info['state']
            info['pincode'] = getattr(comp, 'pincode', None) or info['pincode']
            info['gstin'] = getattr(comp, 'gstin', None) or info['gstin']
            info['pan'] = getattr(comp, 'pan', None) or info['pan']
            info['cin'] = getattr(comp, 'cin', None) or info['cin']
            info['email'] = getattr(comp, 'email', None) or info['email']
            info['phone'] = getattr(comp, 'phone', None) or info['phone']
            info['bank_name'] = getattr(comp, 'bank_name', None) or info['bank_name']
            info['account_no'] = getattr(comp, 'account_no', None) or info['account_no']
            info['ifsc'] = getattr(comp, 'ifsc', None) or info['ifsc']
            info['branch_name'] = getattr(comp, 'branch_name', None) or info['branch_name']
    except Exception as e:
        logger.debug(f"Could not load dynamic company info: {e}")
    return info


def generate_purchase_voucher_pdf(voucher_obj: Any) -> bytes:
    """
    Build a complete, professional Purchase Voucher PDF.
    
    :param voucher_obj: VoucherPurchaseSupplierDetails model instance or dictionary.
    :return: Raw PDF binary bytes.
    """
    buffer = io.BytesIO()

    # 1. Initialize Document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    usable_width = A4[0] - 24 * mm  # ~186 mm

    # 2. Extract Data safely
    def _g(attr, default=""):
        if isinstance(voucher_obj, dict):
            return voucher_obj.get(attr, default)
        return getattr(voucher_obj, attr, default) or default

    voucher_no = _g('purchase_voucher_no') or f"PUR-{_g('id', 'NEW')}"
    series = _g('purchase_voucher_series', '')
    voucher_date = str(_g('date', ''))
    supplier_invoice_no = _g('supplier_invoice_no', '')
    supplier_invoice_date = str(_g('supplier_invoice_date', ''))
    grn_ref = _g('grn_reference', '')
    vendor_name = _g('vendor_name', 'Valued Supplier')
    vendor_email = _g('vendor_email', '')
    vendor_gstin = _g('gstin', '')
    branch = _g('branch', '')
    bill_from = _g('bill_from', '')
    ship_from = _g('ship_from', '')
    input_type = _g('input_type', 'Intrastate')
    tenant_id = _g('tenant_id', None)

    company = _get_company_info(tenant_id)

    # Line Items
    items_list = []
    if hasattr(voucher_obj, 'line_items'):
        items_list = list(voucher_obj.line_items.all())
    elif isinstance(voucher_obj, dict):
        items_list = voucher_obj.get('items') or voucher_obj.get('line_items') or []
        if not items_list and voucher_obj.get('supply_inr_details'):
            items_list = voucher_obj['supply_inr_details'].get('items') or []

    # Due Details
    due_obj = getattr(voucher_obj, 'due_details', None) if not isinstance(voucher_obj, dict) else voucher_obj.get('due_details', {})
    tds_it = float(getattr(due_obj, 'tds_it', 0) if hasattr(due_obj, 'tds_it') else (due_obj.get('tds_it') if isinstance(due_obj, dict) else 0) or 0)
    tds_gst = float(getattr(due_obj, 'tds_gst', 0) if hasattr(due_obj, 'tds_gst') else (due_obj.get('tds_gst') if isinstance(due_obj, dict) else 0) or 0)
    advance_paid = float(getattr(due_obj, 'advance_paid', 0) if hasattr(due_obj, 'advance_paid') else (due_obj.get('advance_paid') if isinstance(due_obj, dict) else 0) or 0)
    to_pay = float(getattr(due_obj, 'to_pay', 0) if hasattr(due_obj, 'to_pay') else (due_obj.get('to_pay') if isinstance(due_obj, dict) else 0) or 0)
    terms = getattr(due_obj, 'terms', '') if hasattr(due_obj, 'terms') else (due_obj.get('terms') if isinstance(due_obj, dict) else '') or ''
    posting_note = getattr(due_obj, 'posting_note', '') if hasattr(due_obj, 'posting_note') else (due_obj.get('posting_note') if isinstance(due_obj, dict) else '') or ''

    # Transit Details
    transit_obj = getattr(voucher_obj, 'transit_details', None) if not isinstance(voucher_obj, dict) else voucher_obj.get('transit_details', {})
    transit_mode = getattr(transit_obj, 'mode', '') if hasattr(transit_obj, 'mode') else (transit_obj.get('mode') if isinstance(transit_obj, dict) else '') or ''
    transporter_name = getattr(transit_obj, 'transporter_name', '') if hasattr(transit_obj, 'transporter_name') else (transit_obj.get('transporter_name') if isinstance(transit_obj, dict) else '') or ''
    vehicle_no = getattr(transit_obj, 'vehicle_no', '') if hasattr(transit_obj, 'vehicle_no') else (transit_obj.get('vehicle_no') if isinstance(transit_obj, dict) else '') or ''
    lr_gr_no = getattr(transit_obj, 'lr_gr_consignment', '') if hasattr(transit_obj, 'lr_gr_consignment') else (transit_obj.get('lr_gr_consignment') if isinstance(transit_obj, dict) else '') or ''

    # 3. Typography Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=COLOR_PRIMARY,
        alignment=2 # Right
    )

    company_title = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=COLOR_PRIMARY
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_DARK
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_DARK
    )

    body_muted = ParagraphStyle(
        'DocBodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=COLOR_MUTED
    )

    th_style = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1 # Center
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=COLOR_DARK
    )

    td_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=COLOR_DARK,
        alignment=2 # Right
    )

    td_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10.5,
        textColor=COLOR_PRIMARY,
        alignment=2 # Right
    )

    elements = []

    # ---------------------------------------------------------
    # Header: Company Info + Purchase Voucher Badge
    # ---------------------------------------------------------
    company_lines = [
        Paragraph(f"<b>{company['name']}</b>", company_title),
        Paragraph(company['address'], body_muted),
        Paragraph(f"{company['city']}, {company['state']} - {company['pincode']}", body_muted),
        Paragraph(f"<b>GSTIN:</b> {company['gstin']} &nbsp;|&nbsp; <b>PAN:</b> {company['pan']}", body_muted),
        Paragraph(f"<b>Email:</b> {company['email']} &nbsp;|&nbsp; <b>Phone:</b> {company['phone']}", body_muted)
    ]

    voucher_meta_lines = [
        Paragraph("<b>PURCHASE VOUCHER</b>", title_style),
        Paragraph(f"<b>Voucher No:</b> {voucher_no}", ParagraphStyle('MetaR', parent=td_right_bold, fontSize=10, leading=13)),
        Paragraph(f"<b>Date:</b> {voucher_date}", td_right),
        Paragraph(f"<b>Series:</b> {series or 'Standard'}", td_right),
        Paragraph(f"<b>Supplier Invoice #:</b> {supplier_invoice_no}", td_right),
        Paragraph(f"<b>Supplier Inv Date:</b> {supplier_invoice_date or '-'}", td_right),
    ]
    if grn_ref:
        voucher_meta_lines.append(Paragraph(f"<b>GRN Ref:</b> {grn_ref}", td_right))

    header_table = Table(
        [[company_lines, voucher_meta_lines]],
        colWidths=[usable_width * 0.58, usable_width * 0.42]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceBefore=4, spaceAfter=8))

    # ---------------------------------------------------------
    # Supplier (Bill From / Ship From) & Buyer (Bill To)
    # ---------------------------------------------------------
    supplier_info = [
        Paragraph("<b>SUPPLIER / BILLED FROM:</b>", body_bold),
        Paragraph(f"<b>{vendor_name}</b>" + (f" ({branch})" if branch else ""), body_bold),
        Paragraph(bill_from or "Address not specified", body_style),
        Paragraph(f"<b>GSTIN:</b> {vendor_gstin or 'Unregistered'}", body_style),
    ]
    if vendor_email:
        supplier_info.append(Paragraph(f"<b>Email:</b> {vendor_email}", body_muted))

    buyer_info = [
        Paragraph("<b>RECEIVER / BILLED TO:</b>", body_bold),
        Paragraph(f"<b>{company['name']}</b>", body_bold),
        Paragraph(company['address'] + f", {company['city']}, {company['state']} - {company['pincode']}", body_style),
        Paragraph(f"<b>GSTIN:</b> {company['gstin']}", body_style),
        Paragraph(f"<b>Input Type:</b> {input_type}", body_muted),
    ]

    parties_table = Table(
        [[supplier_info, buyer_info]],
        colWidths=[usable_width * 0.50, usable_width * 0.50]
    )
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # Items Table
    # ---------------------------------------------------------
    headers = [
        Paragraph("#", th_style),
        Paragraph("Item / Description", th_style),
        Paragraph("HSN/SAC", th_style),
        Paragraph("Qty", th_style),
        Paragraph("Rate", th_style),
        Paragraph("Discount", th_style),
        Paragraph("Taxable", th_style),
        Paragraph("GST", th_style),
        Paragraph("Total (₹)", th_style)
    ]

    col_widths = [
        usable_width * 0.05,  # #
        usable_width * 0.28,  # Item
        usable_width * 0.10,  # HSN
        usable_width * 0.08,  # Qty
        usable_width * 0.10,  # Rate
        usable_width * 0.09,  # Discount
        usable_width * 0.11,  # Taxable
        usable_width * 0.08,  # GST %
        usable_width * 0.11   # Total
    ]

    table_data = [headers]

    calc_taxable = Decimal("0.00")
    calc_cgst = Decimal("0.00")
    calc_sgst = Decimal("0.00")
    calc_igst = Decimal("0.00")
    calc_gross = Decimal("0.00")

    def _item_val(it, key, default=0):
        if isinstance(it, dict):
            return it.get(key, default)
        return getattr(it, key, default)

    for idx, item in enumerate(items_list, start=1):
        name = _item_val(item, 'item_name') or _item_val(item, 'name') or f"Item {idx}"
        code = _item_val(item, 'item_code') or ''
        hsn = _item_val(item, 'hsn_sac') or _item_val(item, 'hsnSac') or '-'
        qty = float(_item_val(item, 'quantity') or _item_val(item, 'qty') or 0)
        uom = _item_val(item, 'uom') or ''
        rate = float(_item_val(item, 'rate') or 0)
        disc = float(_item_val(item, 'discount_amount') or _item_val(item, 'discountAmount') or 0)
        taxable = float(_item_val(item, 'taxable_value') or _item_val(item, 'taxableValue') or 0)
        cgst = float(_item_val(item, 'cgst_amount') or _item_val(item, 'cgst') or 0)
        sgst = float(_item_val(item, 'sgst_amount') or _item_val(item, 'sgst') or 0)
        igst = float(_item_val(item, 'igst_amount') or _item_val(item, 'igst') or 0)
        gst_rate = float(_item_val(item, 'gst_rate') or _item_val(item, 'gstRate') or 0)
        row_total = float(_item_val(item, 'invoice_value') or _item_val(item, 'invoiceValue') or (taxable + cgst + sgst + igst))

        calc_taxable += Decimal(str(taxable))
        calc_cgst += Decimal(str(cgst))
        calc_sgst += Decimal(str(sgst))
        calc_igst += Decimal(str(igst))
        calc_gross += Decimal(str(row_total))

        desc_p = [Paragraph(f"<b>{name}</b>", td_style)]
        if code and code != name:
            desc_p.append(Paragraph(f"<font size=7 color='#64748B'>Code: {code}</font>", td_style))

        table_data.append([
            Paragraph(str(idx), td_style),
            desc_p,
            Paragraph(str(hsn), td_style),
            Paragraph(f"{qty:g} {uom}".strip(), td_right),
            Paragraph(_fmt_curr(rate), td_right),
            Paragraph(_fmt_curr(disc) if disc > 0 else "-", td_right),
            Paragraph(_fmt_curr(taxable), td_right),
            Paragraph(f"{gst_rate:g}%" if gst_rate > 0 else "-", td_right),
            Paragraph(_fmt_curr(row_total), td_right_bold)
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]

    # Zebra striping
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.append(('BACKGROUND', (0, i), (-1, i), COLOR_ZEBRA))

    items_table.setStyle(TableStyle(ts))
    elements.append(items_table)
    elements.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # Summary & Totals Box
    # ---------------------------------------------------------
    total_tax = calc_cgst + calc_sgst + calc_igst
    round_off = Decimal(str(round(float(calc_gross)))) - calc_gross
    final_gross = calc_gross + round_off
    final_to_pay = to_pay if to_pay > 0 else float(final_gross - Decimal(str(advance_paid)))

    summary_rows = [
        [Paragraph("Taxable Value:", td_style), Paragraph(f"₹ {_fmt_curr(calc_taxable)}", td_right)],
    ]
    if calc_cgst > 0:
        summary_rows.append([Paragraph("CGST:", td_style), Paragraph(f"₹ {_fmt_curr(calc_cgst)}", td_right)])
    if calc_sgst > 0:
        summary_rows.append([Paragraph("SGST:", td_style), Paragraph(f"₹ {_fmt_curr(calc_sgst)}", td_right)])
    if calc_igst > 0:
        summary_rows.append([Paragraph("IGST:", td_style), Paragraph(f"₹ {_fmt_curr(calc_igst)}", td_right)])
    if abs(round_off) > Decimal("0.001"):
        summary_rows.append([Paragraph("Round Off:", td_style), Paragraph(f"₹ {_fmt_curr(round_off)}", td_right)])
    
    summary_rows.append([
        Paragraph("<b>Total Invoice Value:</b>", body_bold),
        Paragraph(f"<b>₹ {_fmt_curr(final_gross)}</b>", td_right_bold)
    ])
    if advance_paid > 0:
        summary_rows.append([
            Paragraph("Less: Advance Paid:", td_style),
            Paragraph(f"₹ {_fmt_curr(advance_paid)}", td_right)
        ])
    if tds_it > 0:
        summary_rows.append([
            Paragraph("TDS/TCS (IT):", td_style),
            Paragraph(f"₹ {_fmt_curr(tds_it)}", td_right)
        ])
    summary_rows.append([
        Paragraph("<b>Net Payable Balance:</b>", ParagraphStyle('NetPayableL', parent=body_bold, textColor=COLOR_PRIMARY)),
        Paragraph(f"<b>₹ {_fmt_curr(final_to_pay)}</b>", ParagraphStyle('NetPayableR', parent=td_right_bold, fontSize=9.5, textColor=COLOR_PRIMARY))
    ])

    summary_table = Table(summary_rows, colWidths=[usable_width * 0.22, usable_width * 0.20])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -2), (-1, -2), 0.5, COLOR_BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT),
    ]))

    # Left box: Amount in Words + Terms / Transit / Notes
    words_text = _num_to_words(float(final_gross))
    left_notes = [
        Paragraph(f"<b>Amount in Words:</b> {words_text}", body_style),
        Spacer(1, 4),
    ]

    extra_info_parts = []
    if terms:
        extra_info_parts.append(f"<b>Payment Terms:</b> {terms}")
    if posting_note:
        extra_info_parts.append(f"<b>Notes:</b> {posting_note}")
    if transporter_name or vehicle_no or lr_gr_no:
        transit_str = " &nbsp;|&nbsp; ".join(filter(None, [
            f"Transporter: {transporter_name}" if transporter_name else "",
            f"Vehicle: {vehicle_no}" if vehicle_no else "",
            f"LR/GR: {lr_gr_no}" if lr_gr_no else "",
            f"Mode: {transit_mode}" if transit_mode else ""
        ]))
        extra_info_parts.append(f"<b>Dispatch/Transit:</b> {transit_str}")

    if extra_info_parts:
        for p_str in extra_info_parts:
            left_notes.append(Paragraph(p_str, body_muted))

    left_box_table = Table([[left_notes]], colWidths=[usable_width * 0.55])
    left_box_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    bottom_block = Table(
        [[left_box_table, summary_table]],
        colWidths=[usable_width * 0.56, usable_width * 0.44]
    )
    bottom_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(KeepTogether([bottom_block]))
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # Footer / Signatures
    # ---------------------------------------------------------
    footer_table = Table(
        [[
            [
                Paragraph("<b>Declaration:</b>", body_bold),
                Paragraph("We hereby certify that the goods/services mentioned in this purchase voucher have been received in good order and verified against supplier invoice & purchase orders.", body_muted)
            ],
            [
                Paragraph(f"For <b>{company['name']}</b>", ParagraphStyle('AuthBy', parent=body_style, alignment=2)),
                Spacer(1, 24),
                Paragraph("<b>Authorised Signatory</b>", ParagraphStyle('AuthSig', parent=body_bold, alignment=2))
            ]
        ]],
        colWidths=[usable_width * 0.60, usable_width * 0.40]
    )
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(KeepTogether([footer_table]))

    # 4. Build document
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
