"""
Purchase Order PDF Generator Service
Generates professional, printable Purchase Order PDFs using ReportLab.
"""
import io
import logging
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
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

def generate_po_pdf(po: Dict[str, Any], company: Dict[str, Any]) -> bytes:
    """
    Generate a professional Purchase Order PDF document.
    Returns the PDF as raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#3730a3")   # Indigo 800
    secondary_color = colors.HexColor("#4f46e5") # Indigo 600
    dark_slate = colors.HexColor("#1e293b")      # Slate 800
    muted_slate = colors.HexColor("#64748b")     # Slate 500
    border_slate = colors.HexColor("#e2e8f0")    # Slate 200
    bg_light = colors.HexColor("#f8fafc")        # Slate 50

    title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=muted_slate
    )

    po_badge_title = ParagraphStyle(
        'POBadgeTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.white,
        alignment=2 # Right
    )

    po_badge_sub = ParagraphStyle(
        'POBadgeSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#e0e7ff"),
        alignment=2 # Right
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=secondary_color,
        textTransform='uppercase'
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=dark_slate
    )

    body_normal = ParagraphStyle(
        'BodyNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=dark_slate
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
        alignment=1 # Center
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=dark_slate
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=dark_slate
    )

    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=dark_slate,
        alignment=2 # Right
    )

    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=secondary_color,
        alignment=2 # Right
    )

    story = []

    # 1. Header Banner Table
    po_number = str(po.get('po_number', 'PO-N/A'))
    po_date = str(po.get('po_date') or po.get('created_at') or '')[:10]
    
    comp_lines = [
        f"<b>{company.get('name', 'Finpixe Enterprise')}</b>",
        company.get('branch_name', ''),
        company.get('address', ''),
        company.get('city_state', ''),
        f"GSTIN: {company.get('gstin')}" if company.get('gstin') else ""
    ]
    comp_text = "<br/>".join([c for c in comp_lines if c])
    
    left_header = Paragraph(comp_text, subtitle_style)
    
    right_badge = [
        Paragraph("<b>PURCHASE ORDER</b>", po_badge_title),
        Paragraph(f"PO No: <b>{po_number}</b>", po_badge_title),
        Paragraph(f"Date: {po_date}", po_badge_sub),
        Paragraph("Status: <b>Approved & Issued</b>", po_badge_sub)
    ]
    
    header_data = [
        [left_header, right_badge]
    ]
    
    header_table = Table(header_data, colWidths=[310, 212])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (1,0), (1,0), primary_color),
        ('PADDING', (1,0), (1,0), 8),
        ('TOPPADDING', (0,0), (0,0), 0),
        ('BOTTOMPADDING', (0,0), (0,0), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 14))

    # 2. Two-Column Vendor & Shipping Box
    vendor_name = po.get('vendor_name') or 'Valued Vendor'
    vendor_branch = po.get('branch') or ''
    vendor_email = po.get('email_address') or ''
    contract_no = po.get('contract_no') or '-'
    
    v_addr_parts = [p for p in [po.get('address_line1'), po.get('address_line2'), po.get('address_line3')] if p]
    v_address = ', '.join(v_addr_parts)
    v_loc_parts = [p for p in [po.get('city'), po.get('state'), po.get('pincode'), po.get('country')] if p]
    v_location = ', '.join(v_loc_parts)

    receive_by = str(po.get('receive_by') or '-')[:10]
    receive_at = po.get('receive_at') or '-'
    delivery_terms = po.get('delivery_terms') or 'Standard delivery terms apply.'

    vendor_box = [
        Paragraph("<b>VENDOR / SUPPLIER</b>", section_header_style),
        Spacer(1, 3),
        Paragraph(f"<b>{vendor_name}</b>", body_bold),
        Paragraph(f"Branch: {vendor_branch}" if vendor_branch else "", body_normal),
        Paragraph(v_address, body_normal),
        Paragraph(v_location, body_normal),
        Paragraph(f"Email: <b>{vendor_email}</b>" if vendor_email else "", body_normal),
        Paragraph(f"Contract / Ref No: <b>{contract_no}</b>", body_normal),
    ]

    shipping_box = [
        Paragraph("<b>SHIPPING & DELIVERY</b>", section_header_style),
        Spacer(1, 3),
        Paragraph(f"<b>Expected By (Receive By):</b> {receive_by}", body_normal),
        Paragraph(f"<b>Receive At Location:</b> {receive_at}", body_normal),
        Spacer(1, 4),
        Paragraph(f"<b>Terms:</b> {delivery_terms}", body_normal),
    ]

    parties_table = Table([[vendor_box, shipping_box]], colWidths=[261, 261])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, border_slate),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_slate),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(parties_table)
    story.append(Spacer(1, 14))

    # 3. Line Items Table
    items: List[Dict[str, Any]] = po.get('items') or []
    
    table_data = [
        [
            Paragraph("<b>#</b>", table_header_style),
            Paragraph("<b>Item Description</b>", table_header_style),
            Paragraph("<b>Qty</b>", table_header_style),
            Paragraph("<b>UOM</b>", table_header_style),
            Paragraph("<b>Rate</b>", table_header_style),
            Paragraph("<b>Taxable</b>", table_header_style),
            Paragraph("<b>Tax</b>", table_header_style),
            Paragraph("<b>Total</b>", table_header_style)
        ]
    ]

    col_widths = [24, 160, 42, 40, 60, 64, 62, 70] # Total = 522 pt

    for idx, it in enumerate(items, 1):
        code = it.get('item_code') or '-'
        name = it.get('item_name') or '-'
        supplier_code = it.get('supplier_item_code') or ''
        qty = _format_qty(it.get('quantity'))
        uom = it.get('uom') or 'Units'
        rate = _format_currency(it.get('final_rate') or it.get('negotiated_rate'))
        taxable = _format_currency(it.get('taxable_value'))
        gst_rate = f"{float(it.get('gst_rate') or 0):g}%"
        gst_amt = _format_currency(it.get('gst_amount'))
        inv_val = _format_currency(it.get('invoice_value'))

        item_desc = f"<b>{name}</b><br/><font size='7' color='#64748b'>Code: {code}{' | Ref: ' + supplier_code if supplier_code else ''}</font>"

        table_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(item_desc, table_cell_style),
            Paragraph(qty, table_cell_style),
            Paragraph(uom, table_cell_style),
            Paragraph(rate, table_cell_right),
            Paragraph(taxable, table_cell_right),
            Paragraph(f"{gst_amt}<br/><font size='6.5' color='#64748b'>({gst_rate})</font>", table_cell_right),
            Paragraph(inv_val, table_cell_right_bold)
        ])

    if len(items) == 0:
        table_data.append([
            Paragraph("-", table_cell_style),
            Paragraph("No line items listed.", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, border_slate),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
    ]))

    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary & Instructions Box
    total_taxable = _format_currency(po.get('total_taxable_value'))
    total_tax = _format_currency(po.get('total_tax'))
    total_value = _format_currency(po.get('total_value'))

    instructions_text = """
    <b>Terms &amp; Instructions:</b><br/>
    1. Quote PO Number on all delivery challans, bills, and packages.<br/>
    2. Deliveries must conform strictly to ordered specifications and quantity.<br/>
    3. Goods subject to inspection and approval upon delivery.
    """
    instructions_p = Paragraph(instructions_text, body_normal)

    totals_table_data = [
        [Paragraph("Taxable Subtotal:", body_normal), Paragraph(total_taxable, table_cell_right_bold)],
        [Paragraph("Total GST Tax:", body_normal), Paragraph(total_tax, table_cell_right_bold)],
        [Paragraph("<b>TOTAL PO VALUE:</b>", body_bold), Paragraph(f"<b>{total_value}</b>", ParagraphStyle('GrandTotal', parent=table_cell_right_bold, fontSize=10, textColor=primary_color))]
    ]
    totals_table = Table(totals_table_data, colWidths=[110, 110])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,1), (1,1), 0.5, border_slate),
        ('BACKGROUND', (0,2), (1,2), colors.HexColor("#e0e7ff")),
        ('PADDING', (0,2), (1,2), 5),
    ]))

    summary_table = Table([[instructions_p, totals_table]], colWidths=[302, 220])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))

    story.append(KeepTogether([summary_table, Spacer(1, 20)]))

    # 5. Signature and Certification Block
    sig_data = [
        [
            Paragraph("Prepared By / Purchasing Officer<br/><font size='7' color='#94a3b8'>Generated Systematically</font>", body_normal),
            Paragraph("Authorized Signatory<br/><font size='7' color='#94a3b8'>For " + company.get('name', 'Company') + "</font>", ParagraphStyle('AuthSig', parent=body_normal, alignment=2))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[261, 261])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor("#94a3b8")),
        ('LINEABOVE', (1,0), (1,0), 0.5, colors.HexColor("#94a3b8")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))

    story.append(KeepTogether([sig_table, Spacer(1, 10)]))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
