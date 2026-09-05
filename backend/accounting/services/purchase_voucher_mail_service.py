"""
Purchase Voucher Email Dispatch Service
---------------------------------------
Builds an executive-grade HTML email template and sends the Purchase Voucher
to the vendor/supplier via SMTP, with the dynamically generated Purchase Voucher PDF
and any uploaded supporting documents attached.
"""

import os
import mimetypes
import logging
from typing import Dict, Any, Optional, List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger("accounting.purchase_mail")


def _build_purchase_email_html(
    voucher_obj: Any,
    company: Dict[str, Any],
    items_count: int,
    total_amount: str,
    due_amount: str
) -> str:
    """Build a branded HTML email body for Purchase Voucher notification."""
    def _g(attr, default=""):
        if isinstance(voucher_obj, dict):
            return voucher_obj.get(attr, default)
        return getattr(voucher_obj, attr, default) or default

    voucher_no = _g('purchase_voucher_no') or f"PUR-{_g('id', 'NEW')}"
    supplier_inv_no = _g('supplier_invoice_no', '')
    date_str = str(_g('date', ''))
    vendor_name = _g('vendor_name', 'Valued Supplier')
    company_name = company.get('name') or company.get('company_name') or 'Finpixe Enterprises'
    company_phone = company.get('phone', '')
    company_email = company.get('email', '')
    company_gstin = company.get('gstin', '')

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Purchase Voucher {voucher_no}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #F8FAFC;
      color: #1E293B;
      -webkit-font-smoothing: antialiased;
    }}
    .email-container {{
      max-width: 600px;
      margin: 30px auto;
      background: #FFFFFF;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
      border: 1px solid #E2E8F0;
    }}
    .header {{
      background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
      padding: 32px 28px;
      color: #FFFFFF;
      text-align: left;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .header p {{
      margin: 6px 0 0 0;
      font-size: 13px;
      color: #BFDBFE;
    }}
    .content {{
      padding: 28px;
    }}
    .greeting {{
      font-size: 15px;
      line-height: 1.6;
      color: #334155;
      margin-bottom: 20px;
    }}
    .summary-card {{
      background-color: #F1F5F9;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 24px;
      border: 1px solid #E2E8F0;
    }}
    .summary-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #E2E8F0;
      font-size: 14px;
    }}
    .summary-row:last-child {{
      border-bottom: none;
      padding-top: 12px;
      font-weight: 700;
      font-size: 16px;
      color: #1E3A8A;
    }}
    .summary-label {{
      color: #64748B;
    }}
    .summary-value {{
      font-weight: 600;
      color: #0F172A;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      background-color: #DBEAFE;
      color: #1E40AF;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }}
    .notice-box {{
      background-color: #EFF6FF;
      border-left: 4px solid #3B82F6;
      padding: 14px 16px;
      border-radius: 4px;
      margin-bottom: 24px;
      font-size: 13px;
      color: #1E40AF;
      line-height: 1.5;
    }}
    .footer {{
      background-color: #F8FAFC;
      padding: 20px 28px;
      border-top: 1px solid #E2E8F0;
      text-align: center;
      font-size: 12px;
      color: #94A3B8;
      line-height: 1.6;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <span class="badge" style="background: rgba(255,255,255,0.2); color: #fff; margin-bottom: 8px;">PURCHASE CONFIRMATION</span>
      <h1>Purchase Voucher {voucher_no}</h1>
      <p>{company_name} &bull; GSTIN: {company_gstin}</p>
    </div>
    
    <div class="content">
      <div class="greeting">
        Dear <b>{vendor_name}</b>,<br><br>
        This is to confirm that Purchase Voucher <b>#{voucher_no}</b> has been recorded for your Invoice <b>#{supplier_inv_no}</b> dated <b>{date_str}</b>.
      </div>
      
      <div class="summary-card">
        <div class="summary-row">
          <span class="summary-label">Purchase Voucher No:</span>
          <span class="summary-value">{voucher_no}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Supplier Invoice No:</span>
          <span class="summary-value">{supplier_inv_no}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Voucher Date:</span>
          <span class="summary-value">{date_str}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Items Count:</span>
          <span class="summary-value">{items_count} Item(s)</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Total Gross Amount:</span>
          <span class="summary-value">₹ {total_amount}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Net Payable Balance:</span>
          <span class="summary-value" style="color: #1E3A8A;">₹ {due_amount}</span>
        </div>
      </div>
      
      <div class="notice-box">
        📎 <b>Attached Documents:</b><br>
        Please find attached the official <b>Purchase Voucher PDF</b> and all associated supporting documents (invoices, receipts, delivery slips) for your accounting records.
      </div>
      
      <p style="font-size: 13px; color: #64748B; margin: 0;">
        If you have any questions or require further details regarding this transaction, please reach out to our accounts department at <a href="mailto:{company_email}" style="color: #3B82F6;">{company_email}</a> or call {company_phone}.
      </p>
    </div>
    
    <div class="footer">
      This is an automated transaction confirmation generated by <b>{company_name}</b>.<br>
      Finpixe AI Accounting &bull; All Rights Reserved.
    </div>
  </div>
</body>
</html>
"""
    return html


def send_purchase_voucher_email(
    voucher_obj: Any,
    recipient_email: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    extra_recipients: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate PDF and dispatch Purchase Voucher email with attachments.
    
    :param voucher_obj: VoucherPurchaseSupplierDetails instance or dict.
    :param recipient_email: Primary recipient email (defaults to voucher_obj.vendor_email).
    :param pdf_bytes: Pre-generated PDF bytes (optional, will generate if omitted).
    :param extra_recipients: Optional list of additional CC emails.
    :return: dict status with success flag and detail message.
    """
    def _g(attr, default=""):
        if isinstance(voucher_obj, dict):
            return voucher_obj.get(attr, default)
        return getattr(voucher_obj, attr, default) or default

    # 1. Determine Recipient(s)
    to_email = (recipient_email or _g('vendor_email', '')).strip()
    
    # Fallback to VendorMasterBasicDetail email if empty
    if not to_email and hasattr(voucher_obj, 'vendor_basic_detail') and voucher_obj.vendor_basic_detail:
        to_email = getattr(voucher_obj.vendor_basic_detail, 'email', '') or ''
    
    recipients = [e.strip() for e in [to_email] if e and '@' in e]
    if extra_recipients:
        recipients.extend([e.strip() for e in extra_recipients if e and '@' in e and e.strip() not in recipients])

    if not recipients:
        logger.warning("No valid recipient email found for Purchase Voucher %s", _g('purchase_voucher_no'))
        return {
            'success': False,
            'message': 'No recipient email specified for this vendor. Please provide a valid vendor email.'
        }

    # 2. Get company details & calculate totals
    from .purchase_voucher_pdf_service import _get_company_info, _fmt_curr, generate_purchase_voucher_pdf

    tenant_id = _g('tenant_id', None)
    company = _get_company_info(tenant_id)
    voucher_no = _g('purchase_voucher_no') or f"PUR-{_g('id', 'NEW')}"
    supplier_inv_no = _g('supplier_invoice_no', '')

    items_list = []
    if hasattr(voucher_obj, 'line_items'):
        items_list = list(voucher_obj.line_items.all())
    elif isinstance(voucher_obj, dict):
        items_list = voucher_obj.get('items') or voucher_obj.get('line_items') or []
        if not items_list and voucher_obj.get('supply_inr_details'):
            items_list = voucher_obj['supply_inr_details'].get('items') or []

    items_count = len(items_list)
    total_val = 0.0
    for it in items_list:
        val = it.get('invoice_value') or it.get('invoiceValue') if isinstance(it, dict) else getattr(it, 'invoice_value', 0)
        try:
            total_val += float(val or 0)
        except (ValueError, TypeError):
            pass

    due_obj = getattr(voucher_obj, 'due_details', None) if not isinstance(voucher_obj, dict) else voucher_obj.get('due_details', {})
    to_pay = float(getattr(due_obj, 'to_pay', 0) if hasattr(due_obj, 'to_pay') else (due_obj.get('to_pay') if isinstance(due_obj, dict) else 0) or total_val)

    total_str = _fmt_curr(total_val)
    due_str = _fmt_curr(to_pay)

    # 3. Generate PDF if not provided
    if not pdf_bytes:
        try:
            pdf_bytes = generate_purchase_voucher_pdf(voucher_obj)
        except Exception as e:
            logger.error("Failed to generate Purchase Voucher PDF for %s: %s", voucher_no, e, exc_info=True)
            return {
                'success': False,
                'message': f"Failed to generate Purchase Voucher PDF: {str(e)}"
            }

    # 4. Construct Email
    company_name = company.get('name') or company.get('company_name') or 'Finpixe Enterprises'
    subject = f"Purchase Voucher Confirmation #{voucher_no} - {company_name}"
    if supplier_inv_no:
        subject += f" (Ref: Inv #{supplier_inv_no})"

    html_content = _build_purchase_email_html(
        voucher_obj=voucher_obj,
        company=company,
        items_count=items_count,
        total_amount=total_str,
        due_amount=due_str
    )
    plain_text_content = strip_tags(html_content)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'accounts@finpixe.com'

    email_msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text_content,
        from_email=from_email,
        to=recipients
    )
    email_msg.attach_alternative(html_content, "text/html")

    # 5. Attach Generated Purchase Voucher PDF
    clean_voucher_num = "".join(c for c in voucher_no if c.isalnum() or c in ('-', '_'))
    pdf_filename = f"Purchase_Voucher_{clean_voucher_num}.pdf"
    email_msg.attach(pdf_filename, pdf_bytes, "application/pdf")
    logger.info("Attached generated Purchase Voucher PDF %s (%d bytes)", pdf_filename, len(pdf_bytes))

    # 6. Attach Uploaded Supporting Document (if available)
    try:
        doc_file = None
        if hasattr(voucher_obj, 'supporting_document') and voucher_obj.supporting_document:
            doc_file = voucher_obj.supporting_document
        elif isinstance(voucher_obj, dict) and voucher_obj.get('supporting_document'):
            doc_file = voucher_obj.get('supporting_document')

        if doc_file:
            # If doc_file is a FieldFile
            if hasattr(doc_file, 'path') and os.path.exists(doc_file.path):
                with open(doc_file.path, 'rb') as f:
                    doc_bytes = f.read()
                filename = os.path.basename(doc_file.path)
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or 'application/octet-stream'
                email_msg.attach(filename, doc_bytes, mime_type)
                logger.info("Attached supporting document %s (%d bytes)", filename, len(doc_bytes))
            elif hasattr(doc_file, 'read'):
                doc_bytes = doc_file.read()
                filename = getattr(doc_file, 'name', 'supporting_document.pdf')
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or 'application/octet-stream'
                email_msg.attach(filename, doc_bytes, mime_type)
                logger.info("Attached supporting document %s (%d bytes)", filename, len(doc_bytes))
    except Exception as e:
        logger.warning("Could not attach supporting document to Purchase Voucher email: %s", e)

    # 7. Dispatch via SMTP
    try:
        email_msg.send(fail_silently=False)
        logger.info("✅ Purchase Voucher %s successfully emailed to: %s", voucher_no, ", ".join(recipients))
        return {
            'success': True,
            'message': f"Purchase Voucher {voucher_no} successfully emailed to {', '.join(recipients)}",
            'recipients': recipients
        }
    except Exception as e:
        logger.error("Failed to transmit Purchase Voucher email for %s: %s", voucher_no, e, exc_info=True)
        return {
            'success': False,
            'message': f"Email delivery failed: {str(e)}"
        }
