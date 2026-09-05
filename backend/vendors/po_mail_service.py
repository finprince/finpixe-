"""
Purchase Order Email Service
Generates professional HTML Purchase Order emails and sends them via Django SMTP.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from . import vendorpo_database as db
from core.models import Tenant, User

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
    """Fetch company / branch information for the header of the PO email."""
    company_info = {
        'name': 'Enterprise AI Accounting',
        'branch_name': '',
        'gstin': '',
        'pan': '',
        'address': '',
        'city_state': '',
        'phone': '',
        'email': '',
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

def generate_po_html(po: Dict[str, Any], company: Dict[str, Any]) -> str:
    """Generate modern, executive-grade HTML for the purchase order."""
    po_number = po.get('po_number', 'PO-N/A')
    po_date = str(po.get('po_date') or po.get('created_at') or '')[:10]
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
    
    total_taxable = _format_currency(po.get('total_taxable_value'))
    total_tax = _format_currency(po.get('total_tax'))
    total_value = _format_currency(po.get('total_value'))
    
    items: List[Dict[str, Any]] = po.get('items') or []
    
    item_rows_html = ""
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
        
        item_rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
            <td style="padding: 12px 10px; color: #64748b; text-align: center;">{idx}</td>
            <td style="padding: 12px 10px; font-weight: 600; color: #1e293b;">
                {name}
                <div style="font-size: 11px; color: #64748b; font-weight: 400; margin-top: 2px;">
                    Code: <span style="font-family: monospace;">{code}</span>
                    {f" | Supplier Ref: {supplier_code}" if supplier_code else ""}
                </div>
            </td>
            <td style="padding: 12px 10px; text-align: center; color: #1e293b; font-weight: 600;">{qty} <span style="font-size: 11px; color: #64748b; font-weight: normal;">{uom}</span></td>
            <td style="padding: 12px 10px; text-align: right; color: #334155;">{rate}</td>
            <td style="padding: 12px 10px; text-align: right; color: #334155;">{taxable}</td>
            <td style="padding: 12px 10px; text-align: right; color: #64748b;">
                <span style="font-size: 11px; background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px;">{gst_rate}</span>
                <div style="font-size: 11px; color: #475569; margin-top: 2px;">{gst_amt}</div>
            </td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 700; color: #4f46e5;">{inv_val}</td>
        </tr>
        """

    if not item_rows_html:
        item_rows_html = """
        <tr>
            <td colspan="7" style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px;">No items listed in this purchase order.</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Purchase Order {po_number}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 30px 10px;">
            <tr>
                <td align="center">
                    <table width="680" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
                        
                        <!-- HEADER BAR -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); padding: 28px 32px; color: #ffffff;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td>
                                            <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; text-transform: uppercase;">
                                                {company['name']}
                                            </h1>
                                            {f"<p style='margin: 4px 0 0 0; font-size: 12px; opacity: 0.85; font-weight: 500;'>{company['branch_name']}</p>" if company['branch_name'] else ""}
                                            {f"<p style='margin: 4px 0 0 0; font-size: 11px; opacity: 0.75;'>GSTIN: {company['gstin']}</p>" if company['gstin'] else ""}
                                        </td>
                                        <td align="right" style="vertical-align: top;">
                                            <div style="background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); padding: 8px 16px; border-radius: 8px; text-align: right; display: inline-block;">
                                                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #c7d2fe;">Purchase Order</div>
                                                <div style="font-size: 16px; font-weight: 800; color: #ffffff; margin-top: 2px;">{po_number}</div>
                                                <div style="font-size: 11px; color: #e0e7ff; margin-top: 2px;">Date: {po_date}</div>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- STATUS BADGE BANNER -->
                        <tr>
                            <td style="background-color: #ecfdf5; border-bottom: 1px solid #a7f3d0; padding: 10px 32px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="color: #065f46; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                            &#10004; Status: Approved &amp; Issued to Vendor
                                        </td>
                                        <td align="right" style="color: #047857; font-size: 11px; font-weight: 600;">
                                            Contract No: {contract_no}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- PARTIES INFO SECTION -->
                        <tr>
                            <td style="padding: 28px 32px 16px 32px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <!-- VENDOR DETAILS -->
                                        <td width="48%" style="vertical-align: top; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                                            <div style="font-size: 10px; font-weight: 800; color: #6366f1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">
                                                VENDOR / SUPPLIER
                                            </div>
                                            <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                                                {vendor_name}
                                            </div>
                                            {f"<div style='font-size: 12px; color: #475569; margin-bottom: 2px;'>Branch: {vendor_branch}</div>" if vendor_branch else ""}
                                            {f"<div style='font-size: 12px; color: #475569; margin-bottom: 2px;'>{v_address}</div>" if v_address else ""}
                                            {f"<div style='font-size: 12px; color: #475569; margin-bottom: 2px;'>{v_location}</div>" if v_location else ""}
                                            {f"<div style='font-size: 12px; color: #4f46e5; margin-top: 6px;'>Email: <strong>{vendor_email}</strong></div>" if vendor_email else ""}
                                        </td>

                                        <td width="4%">&nbsp;</td>

                                        <!-- DELIVERY DETAILS -->
                                        <td width="48%" style="vertical-align: top; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                                            <div style="font-size: 10px; font-weight: 800; color: #6366f1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">
                                                SHIPPING &amp; DELIVERY
                                            </div>
                                            <div style="font-size: 12px; color: #334155; margin-bottom: 6px;">
                                                <strong>Expected By:</strong> <span style="color: #0f172a; font-weight: 600;">{receive_by}</span>
                                            </div>
                                            <div style="font-size: 12px; color: #334155; margin-bottom: 6px;">
                                                <strong>Receive At:</strong> <span style="color: #0f172a; font-weight: 600;">{receive_at}</span>
                                            </div>
                                            <div style="font-size: 11px; color: #64748b; margin-top: 8px; line-height: 1.4; border-top: 1px dashed #cbd5e1; pt-6; padding-top: 6px;">
                                                <strong>Terms:</strong> {delivery_terms}
                                            </div>
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
                                            <th style="padding: 10px; text-align: right; width: 85px;">Rate</th>
                                            <th style="padding: 10px; text-align: right; width: 85px;">Taxable</th>
                                            <th style="padding: 10px; text-align: right; width: 75px;">Tax</th>
                                            <th style="padding: 10px; text-align: right; width: 95px;">Total</th>
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
                                                    <li>Please quote PO Number <strong>{po_number}</strong> on all delivery challans and invoices.</li>
                                                    <li>Deliveries must be made to the designated location on or before {receive_by}.</li>
                                                    <li>For queries regarding this PO, please contact your purchasing representative.</li>
                                                </ul>
                                            </div>
                                        </td>
                                        <td width="50%" style="vertical-align: top;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                                                <tr>
                                                    <td style="font-size: 12px; color: #64748b; padding-bottom: 6px;">Total Taxable Value:</td>
                                                    <td align="right" style="font-size: 13px; font-weight: 600; color: #334155; padding-bottom: 6px;">{total_taxable}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 12px; color: #64748b; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">Total GST Tax:</td>
                                                    <td align="right" style="font-size: 13px; font-weight: 600; color: #334155; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">{total_tax}</td>
                                                </tr>
                                                <tr>
                                                    <td style="font-size: 14px; font-weight: 800; color: #0f172a; padding-top: 10px;">Total PO Value:</td>
                                                    <td align="right" style="font-size: 18px; font-weight: 800; color: #4f46e5; padding-top: 10px;">{total_value}</td>
                                                </tr>
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
                                    This is an official system-generated Purchase Order issued via Finpixe Enterprise Accounting.
                                </p>
                                <p style="margin: 0; font-size: 10px; color: #94a3b8;">
                                    Confidential &bull; Sent to {vendor_email or 'Vendor'} &bull; Generated on {po_date}
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

def generate_po_text(po: Dict[str, Any], company: Dict[str, Any]) -> str:
    """Generate clean plain text version of the purchase order."""
    po_number = po.get('po_number', 'PO-N/A')
    po_date = str(po.get('po_date') or po.get('created_at') or '')[:10]
    vendor_name = po.get('vendor_name') or 'Valued Vendor'
    items: List[Dict[str, Any]] = po.get('items') or []
    
    text = f"""
================================================================================
PURCHASE ORDER: {po_number}
================================================================================
Issued by: {company['name']} {f"({company['branch_name']})" if company['branch_name'] else ""}
Date: {po_date}
Status: Approved & Issued

VENDOR:
{vendor_name}
Email: {po.get('email_address') or '-'}
Contract No: {po.get('contract_no') or '-'}

DELIVERY DETAILS:
Expected By: {str(po.get('receive_by') or '-')[:10]}
Receive At: {po.get('receive_at') or '-'}
Terms: {po.get('delivery_terms') or 'Standard terms apply.'}

--------------------------------------------------------------------------------
LINE ITEMS:
--------------------------------------------------------------------------------
"""
    for idx, it in enumerate(items, 1):
        text += f"{idx}. {it.get('item_name')} ({it.get('item_code')}) | Qty: {it.get('quantity')} {it.get('uom')} | Rate: Rs.{it.get('final_rate')} | Total: Rs.{it.get('invoice_value')}\n"

    text += f"""
--------------------------------------------------------------------------------
Total Taxable Value: Rs.{po.get('total_taxable_value', 0)}
Total Tax: Rs.{po.get('total_tax', 0)}
TOTAL PO VALUE: Rs.{po.get('total_value', 0)}
================================================================================
This is an official system-generated Purchase Order.
"""
    return text

def get_vendor_email_from_master(po_data: Dict[str, Any]) -> Optional[str]:
    """Look up the vendor's actual registered email from VendorMasterBasicDetail."""
    vendor_id = po_data.get('vendor_basic_detail_id')
    vendor_name = po_data.get('vendor_name')
    tenant_id = po_data.get('tenant_id')

    try:
        from .models import VendorMasterBasicDetail
        if vendor_id:
            vendor = VendorMasterBasicDetail.objects.filter(id=vendor_id).first()
            if vendor and _is_valid_email(vendor.email):
                return vendor.email.strip()
        
        if vendor_name and tenant_id:
            vendor = VendorMasterBasicDetail.objects.filter(tenant_id=tenant_id, vendor_name=vendor_name).first()
            if vendor and _is_valid_email(vendor.email):
                return vendor.email.strip()
            # Try case-insensitive
            vendor = VendorMasterBasicDetail.objects.filter(tenant_id=tenant_id, vendor_name__iexact=vendor_name).first()
            if vendor and _is_valid_email(vendor.email):
                return vendor.email.strip()
    except Exception as e:
        logger.warning(f"Could not look up vendor email from master: {e}")
    
    return None

def send_purchase_order_email(
    po_id: int,
    sender_user: Optional[Any] = None,
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate and dispatch a purchase order email with PDF attachment.
    
    Recipients included:
    1. The vendor's registered email address from Vendor Master (Basic Details)
    2. The email on the PO record (`email_address`)
    3. Any explicitly specified `recipient_email`
    4. The email of the active user who approved/mailed it (`sender_user.email`)
    
    Returns:
        Dict with keys: success (bool), recipients (List[str]), message (str), error (Optional[str])
    """
    try:
        po_data = db.get_purchase_order_by_id(po_id)
        if not po_data:
            return {
                'success': False,
                'error': f'Purchase Order {po_id} not found',
                'recipients': []
            }
        
        tenant_id = po_data.get('tenant_id', '')
        company_info = get_company_details(tenant_id)
        po_number = po_data.get('po_number', f'PO#{po_id}')
        vendor_name = po_data.get('vendor_name') or 'Vendor'
        
        # Build recipient list
        recipients_set = set()

        # 1. Vendor's email from master record (from Vendor Creation Basic Details)
        vendor_master_email = get_vendor_email_from_master(po_data)
        if vendor_master_email:
            recipients_set.add(vendor_master_email)
            # Update PO data email if it was dummy or empty
            current_po_email = po_data.get('email_address') or ''
            if not current_po_email or '@example.com' in current_po_email or '@test.com' in current_po_email:
                po_data['email_address'] = vendor_master_email
        
        # 2. PO's email address (if valid and not a dummy domain)
        po_email = po_data.get('email_address')
        if _is_valid_email(po_email):
            if '@example.com' not in po_email and '@test.com' not in po_email:
                recipients_set.add(po_email.strip())
            
        # 3. Explicit recipient override
        if _is_valid_email(recipient_email):
            if '@example.com' not in recipient_email and '@test.com' not in recipient_email:
                recipients_set.add(recipient_email.strip())

        # 4. Sender user email (if valid and not already added)
        if sender_user and hasattr(sender_user, 'email') and _is_valid_email(sender_user.email):
            recipients_set.add(sender_user.email.strip())
            
        # Fallback if no valid email discovered
        if not recipients_set:
            default_fallback = getattr(settings, 'EMAIL_HOST_USER', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            if _is_valid_email(default_fallback):
                recipients_set.add(default_fallback.strip())
                
        recipients = list(recipients_set)
        
        if not recipients:
            logger.warning(f"No valid recipient email addresses for PO {po_number}")
            return {
                'success': False,
                'error': 'No valid recipient email address found on the vendor master, purchase order, or user profile.',
                'recipients': []
            }
        
        # Generate contents
        subject = f"Purchase Order {po_number} - {company_info['name']}"
        text_body = generate_po_text(po_data, company_info)
        html_body = generate_po_html(po_data, company_info)
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'noreply@finpixe.com')
        
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients
        )
        email_msg.attach_alternative(html_body, "text/html")

        # Generate and attach PDF Purchase Order
        try:
            from .po_pdf_service import generate_po_pdf
            pdf_bytes = generate_po_pdf(po_data, company_info)
            pdf_filename = f"Purchase_Order_{po_number}.pdf".replace(" ", "_").replace("/", "_")
            email_msg.attach(
                filename=pdf_filename,
                content=pdf_bytes,
                mimetype="application/pdf"
            )
            logger.info(f"Attached PDF document {pdf_filename} ({len(pdf_bytes)} bytes) to email.")
        except Exception as pdf_err:
            logger.warning(f"Could not generate/attach PDF for PO {po_number}: {pdf_err}")

        email_msg.send(fail_silently=False)
        
        logger.info(f"✅ Purchase Order {po_number} (with PDF attachment) successfully mailed to: {', '.join(recipients)}")
        
        return {
            'success': True,
            'message': f"Purchase Order {po_number} (with PDF attachment) successfully mailed to {', '.join(recipients)}",
            'recipients': recipients
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Failed to send Purchase Order {po_id} email: {e}")
        return {
            'success': False,
            'error': str(e),
            'recipients': []
        }
