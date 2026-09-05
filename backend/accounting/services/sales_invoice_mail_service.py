"""
Sales Invoice Email Service
Generates professional HTML Tax Invoice emails and sends them via Django SMTP with attached PDF and supporting documents.
"""
import logging
import re
import os
from typing import Dict, Any, List, Optional
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from core.models import Tenant, User
from accounting.models_voucher_sales import VoucherSalesInvoiceDetails

logger = logging.getLogger(__name__)

def _format_currency(val: Any) -> str:
    try:
        f = float(val or 0)
        return f"₹{f:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def _format_qty(val: Any) -> str:
    try:
        f = float(val or 0)
        if f.is_integer():
            return str(int(f))
        return f"{f:g}"
    except (ValueError, TypeError):
        return "0"

def _is_valid_email(email: Optional[str]) -> bool:
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if not email or '@' not in email:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def get_company_details(tenant_id: str) -> Dict[str, Any]:
    """Fetch company / branch information for the header of the sales invoice email."""
    company_info = {
        'name': 'Enterprise AI Accounting',
        'branch_name': '',
        'gstin': '',
        'pan': '',
        'address': '',
        'city_state': '',
        'phone': '',
        'email': '',
        'bank_name': '',
        'bank_account_no': '',
        'bank_ifsc': '',
        'bank_branch': '',
    }
    try:
        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant:
            company_info['name'] = tenant.name or company_info['name']
            company_info['branch_name'] = tenant.branch_name or ''
            company_info['gstin'] = tenant.gstin or ''
            company_info['pan'] = tenant.pan_number or ''
            company_info['phone'] = tenant.phone or ''
            company_info['email'] = tenant.email or ''
            
            addr_parts = [p for p in [tenant.address_line1, tenant.address_line2, tenant.address_line3] if p]
            company_info['address'] = ', '.join(addr_parts)
            
            cs_parts = [p for p in [tenant.city, tenant.state, tenant.pincode, tenant.country] if p]
            company_info['city_state'] = ', '.join(cs_parts)
    except Exception as e:
        logger.warning(f"Could not load tenant details for {tenant_id}: {e}")
    
    return company_info

def get_customer_email_from_master(customer_id: Optional[int], customer_name: Optional[str], tenant_id: str) -> Optional[str]:
    """Look up customer email from CustomerMasterCustomerBasicDetails or GST details."""
    try:
        from customerportal.database import CustomerMasterCustomerBasicDetails, CustomerMasterCustomerGSTDetails
        if customer_id:
            cust = CustomerMasterCustomerBasicDetails.objects.filter(id=customer_id, tenant_id=tenant_id).first()
            if cust and _is_valid_email(cust.email_address):
                return cust.email_address.strip()
            
            # Check GST branch email
            gst_branch = CustomerMasterCustomerGSTDetails.objects.filter(customer_basic_detail_id=customer_id, tenant_id=tenant_id).first()
            if gst_branch and _is_valid_email(gst_branch.branch_email):
                return gst_branch.branch_email.strip()

        if customer_name:
            cust = CustomerMasterCustomerBasicDetails.objects.filter(tenant_id=tenant_id, customer_name__iexact=customer_name.strip()).first()
            if cust and _is_valid_email(cust.email_address):
                return cust.email_address.strip()
    except Exception as e:
        logger.warning(f"Could not look up customer email: {e}")

    return None

def generate_sales_invoice_html(invoice: Dict[str, Any], company: Dict[str, Any]) -> str:
    """Generate modern, executive-grade HTML email for the Tax Invoice."""
    inv_number = invoice.get('sales_invoice_no', 'INV-N/A')
    inv_date = str(invoice.get('date') or invoice.get('created_at') or '')[:10]
    customer_name = invoice.get('customer_name') or 'Valued Customer'
    customer_branch = invoice.get('customer_branch') or ''
    customer_email = invoice.get('customer_email') or ''
    sales_order_no = invoice.get('sales_order_no') or '-'
    gstin = invoice.get('gstin') or 'Unregistered'
    
    pay = invoice.get('payment_details') or {}
    total_taxable = _format_currency(pay.get('payment_taxable_value'))
    total_tax = _format_currency(float(pay.get('payment_cgst') or 0) + float(pay.get('payment_sgst') or 0) + float(pay.get('payment_igst') or 0) + float(pay.get('payment_cess') or 0))
    total_value = _format_currency(pay.get('payment_invoice_value'))
    net_payable = _format_currency(pay.get('payment_payable') or pay.get('payment_invoice_value'))

    items: List[Dict[str, Any]] = invoice.get('items') or []
    
    item_rows_html = ""
    for idx, it in enumerate(items, 1):
        code = it.get('item_code') or '-'
        name = it.get('item_name') or '-'
        qty = _format_qty(it.get('qty'))
        uom = it.get('uom') or 'Units'
        rate = _format_currency(it.get('item_rate'))
        taxable = _format_currency(it.get('taxable_value'))
        inv_val = _format_currency(it.get('invoice_value'))
        
        item_rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
            <td style="padding: 12px 10px; color: #64748b; text-align: center;">{idx}</td>
            <td style="padding: 12px 10px; font-weight: 600; color: #1e293b;">
                {name}
                <div style="font-size: 11px; color: #64748b; font-weight: 400; margin-top: 2px;">
                    Code: <span style="font-family: monospace;">{code}</span>
                </div>
            </td>
            <td style="padding: 12px 10px; text-align: center; color: #1e293b; font-weight: 600;">{qty} <span style="font-size: 11px; color: #64748b; font-weight: normal;">{uom}</span></td>
            <td style="padding: 12px 10px; text-align: right; color: #334155;">{rate}</td>
            <td style="padding: 12px 10px; text-align: right; color: #334155;">{taxable}</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 700; color: #4338ca;">{inv_val}</td>
        </tr>
        """

    if not item_rows_html:
        item_rows_html = """
        <tr>
            <td colspan="6" style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px;">No items listed in this invoice.</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tax Invoice {inv_number}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 30px 10px;">
            <tr>
                <td align="center">
                    <table width="680" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
                        
                        <!-- HEADER BAR -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #4338ca 0%, #312e81 100%); padding: 28px 32px; color: #ffffff;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td>
                                            <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; text-transform: uppercase;">
                                                {company.get('name', 'Enterprise AI Accounting')}
                                            </h1>
                                            {f"<p style='margin: 4px 0 0 0; font-size: 12px; opacity: 0.85; font-weight: 500;'>{company.get('branch_name')}</p>" if company.get('branch_name') else ""}
                                            {f"<p style='margin: 4px 0 0 0; font-size: 11px; opacity: 0.75;'>GSTIN: {company.get('gstin')}</p>" if company.get('gstin') else ""}
                                        </td>
                                        <td align="right" style="vertical-align: top;">
                                            <div style="background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); padding: 8px 16px; border-radius: 8px; text-align: right; display: inline-block;">
                                                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #c7d2fe;">TAX INVOICE</div>
                                                <div style="font-size: 16px; font-weight: 800; color: #ffffff; margin-top: 2px;">{inv_number}</div>
                                                <div style="font-size: 11px; color: #e0e7ff; margin-top: 2px;">Date: {inv_date}</div>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- BANNER -->
                        <tr>
                            <td style="background-color: #eff6ff; border-bottom: 1px solid #bfdbfe; padding: 10px 32px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="color: #1e40af; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                            &#10004; Official Tax Invoice &amp; Documents Attached
                                        </td>
                                        <td align="right" style="color: #1d4ed8; font-size: 11px; font-weight: 600;">
                                            Order Ref: {sales_order_no}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- CUSTOMER GREETING & INFO -->
                        <tr>
                            <td style="padding: 28px 32px 16px 32px;">
                                <p style="margin: 0 0 16px 0; font-size: 14px; color: #334155; line-height: 1.5;">
                                    Dear <strong>{customer_name}</strong>,<br/>
                                    Please find attached your Tax Invoice (<strong>{inv_number}</strong>) dated <strong>{inv_date}</strong>. The official invoice PDF document and any supporting files are attached to this email.
                                </p>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td width="100%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                                            <div style="font-size: 10px; font-weight: 800; color: #4338ca; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                                                BILLED TO (CUSTOMER DETAILS)
                                            </div>
                                            <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                                                {customer_name}
                                            </div>
                                            {f"<div style='font-size: 12px; color: #475569;'>Branch: {customer_branch}</div>" if customer_branch else ""}
                                            <div style="font-size: 12px; color: #475569;">GSTIN / UIN: <strong>{gstin}</strong></div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- ITEMS TABLE -->
                        <tr>
                            <td style="padding: 16px 32px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                                    <thead>
                                        <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1; font-size: 11px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">
                                            <th style="padding: 10px; text-align: center; width: 30px;">#</th>
                                            <th style="padding: 10px; text-align: left;">Item Description</th>
                                            <th style="padding: 10px; text-align: center; width: 70px;">Qty</th>
                                            <th style="padding: 10px; text-align: right; width: 90px;">Rate</th>
                                            <th style="padding: 10px; text-align: right; width: 95px;">Taxable</th>
                                            <th style="padding: 10px; text-align: right; width: 105px;">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {item_rows_html}
                                    </tbody>
                                </table>
                            </td>
                        </tr>

                        <!-- FINANCIAL SUMMARY SECTION -->
                        <tr>
                            <td style="padding: 8px 32px 28px 32px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td width="50%" style="vertical-align: top; padding-right: 20px;">
                                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; font-size: 11px; color: #64748b; line-height: 1.5;">
                                                <strong style="color: #334155;">Important Instructions:</strong>
                                                <ul style="margin: 6px 0 0 0; padding-left: 18px;">
                                                    <li>Please quote Invoice Number <strong>{inv_number}</strong> on all payments and remittance advice.</li>
                                                    <li>Refer to the attached Tax Invoice PDF document for the complete itemized tax breakdown.</li>
                                                </ul>
                                            </div>
                                        </td>
                                        <td width="50%" style="vertical-align: top;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                                                <tr>
                                                    <td style="font-size: 12px; color: #64748b; padding-bottom: 6px;">Taxable Amount:</td>
                                                    <td align="right" style="font-size: 13px; font-weight: 600; color: #334155; padding-bottom: 6px;">{total_taxable}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 12px; color: #64748b; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">Total Taxes:</td>
                                                    <td align="right" style="font-size: 13px; font-weight: 600; color: #334155; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">{total_tax}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 14px; font-weight: 800; color: #0f172a; padding-top: 10px;">Total Invoice Value:</td>
                                                    <td align="right" style="font-size: 18px; font-weight: 800; color: #4338ca; padding-top: 10px;">{total_value}</td>
                                                </tr>
                                                {f"<tr><td style='font-size: 12px; color: #065f46; font-weight: 700; padding-top: 6px;'>Net Payable:</td><td align='right' style='font-size: 14px; font-weight: 800; color: #065f46; padding-top: 6px;'>{net_payable}</td></tr>" if net_payable != total_value else ""}
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- FOOTER -->
                        <tr>
                            <td style="background-color: #f1f5f9; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center; font-size: 11px; color: #64748b;">
                                <p style="margin: 0 0 4px 0; font-weight: 600; color: #475569;">
                                    This is an official system-generated Tax Invoice issued via Finpixe Enterprise AI Accounting.
                                </p>
                                <p style="margin: 0; font-size: 10px; color: #94a3b8;">
                                    Confidential &bull; Sent to {customer_email or customer_name} &bull; Generated on {inv_date}
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html

def generate_sales_invoice_text(invoice: Dict[str, Any], company: Dict[str, Any]) -> str:
    """Generate clean plain text version of the invoice email."""
    inv_number = invoice.get('sales_invoice_no', 'INV-N/A')
    inv_date = str(invoice.get('date') or invoice.get('created_at') or '')[:10]
    customer_name = invoice.get('customer_name') or 'Valued Customer'
    items: List[Dict[str, Any]] = invoice.get('items') or []
    pay = invoice.get('payment_details') or {}

    text = f"""
================================================================================
TAX INVOICE: {inv_number}
================================================================================
Issued by: {company.get('name', 'Enterprise AI Accounting')} {f"({company.get('branch_name')})" if company.get('branch_name') else ""}
Date: {inv_date}

CUSTOMER / BILLED TO:
{customer_name}
GSTIN: {invoice.get('gstin') or 'Unregistered'}
Order Ref: {invoice.get('sales_order_no') or '-'}

--------------------------------------------------------------------------------
LINE ITEMS:
--------------------------------------------------------------------------------
"""
    for idx, it in enumerate(items, 1):
        text += f"{idx}. {it.get('item_name')} | Qty: {it.get('qty')} {it.get('uom')} | Rate: Rs.{it.get('item_rate')} | Total: Rs.{it.get('invoice_value')}\n"

    text += f"""
--------------------------------------------------------------------------------
Taxable Amount: Rs.{pay.get('payment_taxable_value', 0)}
Total Invoice Value: Rs.{pay.get('payment_invoice_value', 0)}
Net Payable: Rs.{pay.get('payment_payable', pay.get('payment_invoice_value', 0))}
================================================================================
The official Tax Invoice PDF document has been attached to this email.
"""
    return text

def send_sales_invoice_email(
    invoice_id: int,
    recipient_email: Optional[str] = None,
    sender_user: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate and dispatch a Tax Invoice email with attached Invoice PDF and any supporting documents.
    
    Returns:
        Dict with keys: success (bool), recipients (List[str]), message (str), error (Optional[str])
    """
    try:
        invoice_obj = VoucherSalesInvoiceDetails.objects.prefetch_related('items').filter(id=invoice_id).first()
        if not invoice_obj:
            return {
                'success': False,
                'error': f'Sales Invoice {invoice_id} not found',
                'recipients': []
            }
        
        tenant_id = invoice_obj.tenant_id
        company_info = get_company_details(tenant_id)
        
        # Serialize invoice data for email and PDF generator
        from accounting.serializers_voucher_sales import VoucherSalesInvoiceDetailsSerializer
        invoice_data = VoucherSalesInvoiceDetailsSerializer(invoice_obj).data
        
        inv_number = invoice_data.get('sales_invoice_no', f'INV#{invoice_id}')
        customer_name = invoice_data.get('customer_name') or 'Customer'

        # Build recipient set
        recipients_set = set()

        # 1. Explicit recipient override
        if _is_valid_email(recipient_email):
            if '@example.com' not in recipient_email and '@test.com' not in recipient_email:
                recipients_set.add(recipient_email.strip())

        # 2. Email on the invoice record
        inv_email = invoice_data.get('customer_email')
        if _is_valid_email(inv_email):
            if '@example.com' not in inv_email and '@test.com' not in inv_email:
                recipients_set.add(inv_email.strip())

        # 3. Customer registered email from Customer Master
        master_email = get_customer_email_from_master(
            invoice_data.get('customer_id'),
            invoice_data.get('customer_name'),
            tenant_id
        )
        if master_email:
            recipients_set.add(master_email)
            if not invoice_data.get('customer_email'):
                invoice_data['customer_email'] = master_email

        # 4. Fallback: sender user email
        if not recipients_set:
            if sender_user and hasattr(sender_user, 'email') and _is_valid_email(sender_user.email):
                recipients_set.add(sender_user.email.strip())
            else:
                default_fallback = getattr(settings, 'EMAIL_HOST_USER', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                if _is_valid_email(default_fallback):
                    recipients_set.add(default_fallback.strip())

        recipients = list(recipients_set)
        if not recipients:
            logger.warning(f"No valid recipient email address for Sales Invoice {inv_number}")
            return {
                'success': False,
                'error': f'No valid customer email address found for {customer_name}. Please provide a recipient email address.',
                'recipients': []
            }

        subject = f"Tax Invoice {inv_number} from {company_info['name']}"
        text_body = generate_sales_invoice_text(invoice_data, company_info)
        html_body = generate_sales_invoice_html(invoice_data, company_info)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'noreply@finpixe.com')

        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients
        )
        email_msg.attach_alternative(html_body, "text/html")

        # 1. Attach Generated Tax Invoice PDF
        try:
            from .sales_invoice_pdf_service import generate_sales_invoice_pdf
            pdf_bytes = generate_sales_invoice_pdf(invoice_data, company_info)
            pdf_filename = f"Tax_Invoice_{inv_number}.pdf".replace(" ", "_").replace("/", "_")
            email_msg.attach(
                filename=pdf_filename,
                content=pdf_bytes,
                mimetype="application/pdf"
            )
            logger.info(f"Attached generated Tax Invoice PDF {pdf_filename} ({len(pdf_bytes)} bytes)")
        except Exception as pdf_err:
            logger.warning(f"Could not generate/attach PDF for Invoice {inv_number}: {pdf_err}")

        # 2. Attach Supporting Document (if any uploaded)
        try:
            if invoice_obj.supporting_document:
                doc_file = invoice_obj.supporting_document
                doc_name = os.path.basename(doc_file.name)
                # Read content safely
                doc_file.open('rb')
                doc_content = doc_file.read()
                doc_file.close()

                mimetype = "application/pdf" if doc_name.lower().endswith(".pdf") else "image/jpeg"
                email_msg.attach(
                    filename=doc_name,
                    content=doc_content,
                    mimetype=mimetype
                )
                logger.info(f"Attached supporting document {doc_name} ({len(doc_content)} bytes)")
        except Exception as doc_err:
            logger.warning(f"Could not attach supporting document for Invoice {inv_number}: {doc_err}")

        # Send Email
        email_msg.send(fail_silently=False)
        logger.info(f"✅ Tax Invoice {inv_number} successfully emailed to: {', '.join(recipients)}")

        return {
            'success': True,
            'message': f"Tax Invoice {inv_number} successfully emailed to {', '.join(recipients)}",
            'recipients': recipients
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Failed to send Sales Invoice {invoice_id} email: {e}")
        return {
            'success': False,
            'error': str(e),
            'recipients': []
        }
