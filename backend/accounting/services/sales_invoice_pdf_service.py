"""
Sales Invoice PDF Generator Service
Generates professional, GST-compliant Tax Invoice PDFs using ReportLab.
"""
import io
import json
import logging
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

def _format_currency(val: Any) -> str:
    try:
        f = float(val or 0)
        return f"Rs. {f:,.2f}"
    except (ValueError, TypeError):
        return "Rs. 0.00"

def _format_qty(val: Any) -> str:
    try:
        f = float(val or 0)
        if f.is_integer():
            return str(int(f))
        return f"{f:g}"
    except (ValueError, TypeError):
        return "0"

def generate_sales_invoice_pdf(invoice_data: Dict[str, Any], company_info: Dict[str, Any]) -> bytes:
    """
    Generate a professional GST-compliant Tax Invoice PDF document.
    Returns the PDF as raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    # Brand color palette
    primary_color = colors.HexColor("#4338ca")   # Indigo 700
    secondary_color = colors.HexColor("#4f46e5") # Indigo 600
    dark_slate = colors.HexColor("#1e293b")      # Slate 800
    muted_slate = colors.HexColor("#64748b")     # Slate 500
    border_slate = colors.HexColor("#cbd5e1")    # Slate 300
    bg_light = colors.HexColor("#f8fafc")        # Slate 50
    badge_bg = colors.HexColor("#312e81")        # Indigo 900

    title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=primary_color,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=muted_slate
    )

    badge_title = ParagraphStyle(
        'BadgeTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.white,
        alignment=2
    )

    badge_sub = ParagraphStyle(
        'BadgeSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#e0e7ff"),
        alignment=2
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=primary_color,
        textTransform='uppercase'
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=dark_slate
    )

    body_normal = ParagraphStyle(
        'BodyNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_slate
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#ffffff"),
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=dark_slate
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=dark_slate
    )

    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=dark_slate,
        alignment=2
    )

    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=primary_color,
        alignment=2
    )

    story = []

    # 1. Header Banner
    invoice_no = str(invoice_data.get('sales_invoice_no') or 'INV-N/A')
    invoice_date = str(invoice_data.get('date') or '')[:10]
    voucher_name = invoice_data.get('voucher_name') or ''
    sales_order_no = invoice_data.get('sales_order_no') or ''
    reverse_charge = 'Yes' if invoice_data.get('reverse_charge') == 'Y' else 'No'
    place_of_supply = invoice_data.get('place_of_supply') or '-'

    comp_lines = [
        f"<b>{company_info.get('name') or company_info.get('company_name') or 'Enterprise AI Accounting'}</b>",
        company_info.get('branch_name') or '',
        company_info.get('address') or '',
        company_info.get('city_state') or '',
        f"GSTIN: <b>{company_info.get('gstin')}</b>" if company_info.get('gstin') else '',
        f"PAN: {company_info.get('pan')}" if company_info.get('pan') else '',
        f"Ph: {company_info.get('phone')}" if company_info.get('phone') else '',
    ]
    comp_text = "<br/>".join([c for c in comp_lines if c])
    left_header = Paragraph(comp_text, subtitle_style)

    right_badge = [
        Paragraph("<b>TAX INVOICE</b>", badge_title),
        Paragraph(f"Invoice No: <b>{invoice_no}</b>", badge_title),
        Paragraph(f"Date: <b>{invoice_date}</b>", badge_sub),
        Paragraph(f"Voucher Series: {voucher_name}", badge_sub) if voucher_name else None,
        Paragraph(f"Order Ref: {sales_order_no}", badge_sub) if sales_order_no else None,
        Paragraph(f"Reverse Charge: <b>{reverse_charge}</b>", badge_sub),
    ]
    right_badge = [p for p in right_badge if p is not None]

    header_table = Table([[left_header, right_badge]], colWidths=[315, 220])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (1,0), (1,0), badge_bg),
        ('PADDING', (1,0), (1,0), 8),
        ('PADDING', (0,0), (0,0), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 2. Bill To & Ship To Boxes
    customer_name = invoice_data.get('customer_name') or 'Valued Customer'
    customer_branch = invoice_data.get('customer_branch') or ''
    gstin = invoice_data.get('gstin') or 'Unregistered'
    contact = invoice_data.get('contact') or ''
    customer_email = invoice_data.get('customer_email') or ''

    # Parse Bill To
    bill_to_raw = invoice_data.get('bill_to')
    bill_to_dict = {}
    if isinstance(bill_to_raw, str) and bill_to_raw.strip().startswith('{'):
        try:
            bill_to_dict = json.loads(bill_to_raw)
        except Exception:
            bill_to_dict = {}
    elif isinstance(bill_to_raw, dict):
        bill_to_dict = bill_to_raw

    bill_addr_parts = [
        bill_to_dict.get('address_line_1') or bill_to_dict.get('addressLine1') or (bill_to_raw if isinstance(bill_to_raw, str) and not bill_to_raw.startswith('{') else ''),
        bill_to_dict.get('address_line_2') or bill_to_dict.get('addressLine2'),
        bill_to_dict.get('address_line_3') or bill_to_dict.get('addressLine3'),
        bill_to_dict.get('city'),
        bill_to_dict.get('state'),
        bill_to_dict.get('pincode'),
        bill_to_dict.get('country')
    ]
    bill_address_str = ', '.join([p for p in bill_addr_parts if p])

    # Parse Ship To
    ship_to_raw = invoice_data.get('ship_to')
    ship_to_dict = {}
    if isinstance(ship_to_raw, str) and ship_to_raw.strip().startswith('{'):
        try:
            ship_to_dict = json.loads(ship_to_raw)
        except Exception:
            ship_to_dict = {}
    elif isinstance(ship_to_raw, dict):
        ship_to_dict = ship_to_raw

    ship_addr_parts = [
        ship_to_dict.get('address_line_1') or ship_to_dict.get('addressLine1') or (ship_to_raw if isinstance(ship_to_raw, str) and not ship_to_raw.startswith('{') else ''),
        ship_to_dict.get('address_line_2') or ship_to_dict.get('addressLine2'),
        ship_to_dict.get('city'),
        ship_to_dict.get('state'),
        ship_to_dict.get('pincode'),
        ship_to_dict.get('country')
    ]
    ship_address_str = ', '.join([p for p in ship_addr_parts if p]) or bill_address_str or 'Same as Bill To Address'

    bill_to_box = [
        Paragraph("<b>BILLED TO (BUYER)</b>", section_header_style),
        Spacer(1, 2),
        Paragraph(f"<b>{customer_name}</b>", body_bold),
        Paragraph(f"Branch: {customer_branch}", body_normal) if customer_branch else None,
        Paragraph(f"GSTIN / UIN: <b>{gstin}</b>", body_normal),
        Paragraph(bill_address_str if bill_address_str else "Address on record", body_normal),
        Paragraph(f"Contact: {contact}", body_normal) if contact else None,
        Paragraph(f"Email: <b>{customer_email}</b>", body_normal) if customer_email else None,
    ]
    bill_to_box = [p for p in bill_to_box if p is not None]

    ship_to_box = [
        Paragraph("<b>SHIPPED TO (CONSIGNEE)</b>", section_header_style),
        Spacer(1, 2),
        Paragraph(f"<b>{customer_name}</b>", body_bold),
        Paragraph(ship_address_str, body_normal),
        Paragraph(f"Place of Supply: <b>{place_of_supply}</b>", body_normal),
        Paragraph(f"Tax Type: <b>{invoice_data.get('tax_type') or 'Intra-State / Inter-State'}</b>", body_normal),
        Paragraph(f"Nature of Supply: {invoice_data.get('invoice_type') or 'Regular'}", body_normal),
    ]

    parties_table = Table([[bill_to_box, ship_to_box]], colWidths=[267, 268])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, border_slate),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_slate),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))

    # 3. Line Items Table
    items: List[Dict[str, Any]] = invoice_data.get('items') or []
    
    table_data = [
        [
            Paragraph("<b>#</b>", table_header_style),
            Paragraph("<b>Item Description / Service</b>", table_header_style),
            Paragraph("<b>HSN/SAC</b>", table_header_style),
            Paragraph("<b>Qty</b>", table_header_style),
            Paragraph("<b>Rate</b>", table_header_style),
            Paragraph("<b>Taxable</b>", table_header_style),
            Paragraph("<b>CGST</b>", table_header_style),
            Paragraph("<b>SGST</b>", table_header_style),
            Paragraph("<b>IGST</b>", table_header_style),
            Paragraph("<b>Total</b>", table_header_style)
        ]
    ]

    col_widths = [20, 145, 45, 40, 50, 55, 45, 45, 45, 60] # Total = 550 pt

    for idx, it in enumerate(items, 1):
        code = it.get('item_code') or '-'
        name = it.get('item_name') or '-'
        desc = it.get('description') or ''
        hsn = it.get('hsn_sac') or '-'
        qty = _format_qty(it.get('qty'))
        uom = it.get('uom') or 'Units'
        rate = _format_currency(it.get('item_rate'))
        taxable = _format_currency(it.get('taxable_value'))
        cgst = _format_currency(it.get('cgst')) if float(it.get('cgst') or 0) > 0 else "-"
        sgst = _format_currency(it.get('sgst')) if float(it.get('sgst') or 0) > 0 else "-"
        igst = _format_currency(it.get('igst')) if float(it.get('igst') or 0) > 0 else "-"
        inv_val = _format_currency(it.get('invoice_value'))

        item_desc_p = f"<b>{name}</b>"
        if desc:
            item_desc_p += f"<br/><font size='6' color='#64748b'>{desc}</font>"
        if code and code != '-':
            item_desc_p += f"<br/><font size='6' color='#94a3b8'>Code: {code}</font>"

        table_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(item_desc_p, table_cell_style),
            Paragraph(hsn, table_cell_style),
            Paragraph(f"{qty} {uom}", table_cell_style),
            Paragraph(rate, table_cell_right),
            Paragraph(taxable, table_cell_right),
            Paragraph(cgst, table_cell_right),
            Paragraph(sgst, table_cell_right),
            Paragraph(igst, table_cell_right),
            Paragraph(inv_val, table_cell_right_bold)
        ])

    if not items:
        table_data.append([
            Paragraph("-", table_cell_style),
            Paragraph("No line items listed.", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, border_slate),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8))

    # 4. Financial Totals & Payment Summary
    pay = invoice_data.get('payment_details') or {}
    total_taxable = _format_currency(pay.get('payment_taxable_value'))
    total_cgst = _format_currency(pay.get('payment_cgst'))
    total_sgst = _format_currency(pay.get('payment_sgst'))
    total_igst = _format_currency(pay.get('payment_igst'))
    total_cess = _format_currency(pay.get('payment_cess'))
    total_invoice_value = _format_currency(pay.get('payment_invoice_value'))
    total_tds = _format_currency(pay.get('payment_tds_income_tax'))
    total_advance = _format_currency(pay.get('payment_advance'))
    net_payable = _format_currency(pay.get('payment_payable') or pay.get('payment_invoice_value'))

    terms = pay.get('terms_conditions') or company_info.get('terms') or "1. Payment is due as per agreed terms.\n2. Interest @ 18% p.a. will be charged on overdue payments."
    posting_note = pay.get('posting_note') or ''

    # Left: Bank details & Terms
    bank_lines = [
        "<b>Bank Details for Remittance:</b>",
        f"Bank: <b>{company_info.get('bank_name') or 'State Bank of India'}</b>",
        f"A/c No: <b>{company_info.get('bank_account_no') or company_info.get('account_no') or '1234567890'}</b>",
        f"IFSC Code: <b>{company_info.get('bank_ifsc') or company_info.get('ifsc') or 'SBIN0001234'}</b>",
        f"Branch: {company_info.get('bank_branch') or 'Main Branch'}" if company_info.get('bank_branch') else ""
    ]
    bank_p = Paragraph("<br/>".join([b for b in bank_lines if b]), body_normal)
    terms_p = Paragraph(f"<b>Terms & Conditions:</b><br/>{terms.replace(chr(10), '<br/>')}", body_normal)

    left_summary_data = [
        [bank_p],
        [terms_p]
    ]
    if posting_note:
        left_summary_data.append([Paragraph(f"<b>Note:</b> {posting_note}", body_normal)])

    left_summary_table = Table(left_summary_data, colWidths=[300])
    left_summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))

    # Right: Totals Table
    totals_rows = [
        [Paragraph("Taxable Subtotal:", body_normal), Paragraph(total_taxable, table_cell_right_bold)],
    ]
    if float(pay.get('payment_cgst') or 0) > 0:
        totals_rows.append([Paragraph("CGST:", body_normal), Paragraph(total_cgst, table_cell_right)])
    if float(pay.get('payment_sgst') or 0) > 0:
        totals_rows.append([Paragraph("SGST:", body_normal), Paragraph(total_sgst, table_cell_right)])
    if float(pay.get('payment_igst') or 0) > 0:
        totals_rows.append([Paragraph("IGST:", body_normal), Paragraph(total_igst, table_cell_right)])
    if float(pay.get('payment_cess') or 0) > 0:
        totals_rows.append([Paragraph("Cess:", body_normal), Paragraph(total_cess, table_cell_right)])

    totals_rows.append([
        Paragraph("<b>Invoice Total:</b>", body_bold),
        Paragraph(f"<b>{total_invoice_value}</b>", ParagraphStyle('SubTot', parent=table_cell_right_bold, fontSize=8.5))
    ])

    if float(pay.get('payment_tds_income_tax') or 0) > 0:
        totals_rows.append([Paragraph("Less: TDS / TCS:", body_normal), Paragraph(f"-{total_tds}", table_cell_right)])
    if float(pay.get('payment_advance') or 0) > 0:
        totals_rows.append([Paragraph("Less: Advance Paid:", body_normal), Paragraph(f"-{total_advance}", table_cell_right)])

    totals_rows.append([
        Paragraph("<b>NET PAYABLE:</b>", ParagraphStyle('NetH', parent=body_bold, fontSize=9, textColor=primary_color)),
        Paragraph(f"<b>{net_payable}</b>", ParagraphStyle('NetV', parent=table_cell_right_bold, fontSize=9.5, textColor=primary_color))
    ])

    totals_table = Table(totals_rows, colWidths=[115, 120])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, border_slate),
        ('LINEBELOW', (0,-2), (1,-2), 0.5, border_slate),
        ('BACKGROUND', (0,-1), (1,-1), colors.HexColor("#e0e7ff")),
        ('PADDING', (0,-1), (1,-1), 4),
    ]))

    summary_table = Table([[left_summary_table, totals_table]], colWidths=[305, 240])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(KeepTogether([summary_table, Spacer(1, 14)]))

    # 5. Signatory Footer
    sig_data = [
        [
            Paragraph("Prepared By: Accounting Automated System<br/><font size='6.5' color='#94a3b8'>This is a computer generated invoice.</font>", body_normal),
            Paragraph("Authorized Signatory<br/><font size='6.5' color='#94a3b8'>For " + (company_info.get('name') or company_info.get('company_name') or 'Company') + "</font>", ParagraphStyle('AuthSig', parent=body_normal, alignment=2))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 265])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor("#94a3b8")),
        ('LINEABOVE', (1,0), (1,0), 0.5, colors.HexColor("#94a3b8")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(KeepTogether([sig_table]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
