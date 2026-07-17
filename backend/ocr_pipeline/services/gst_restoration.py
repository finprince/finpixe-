import logging

logger = logging.getLogger(__name__)

def sync_nested_totals(ext, cgst, sgst, igst, cess, invoice_total, taxable_total):
    """
    Synchronizes the root header totals to legacy nested representations 
    (sections.supply_details and assembled_exports[0]) inside extracted_data.
    """
    ext['total_cgst'] = cgst
    ext['total_sgst'] = sgst
    ext['total_igst'] = igst
    ext['total_cess'] = cess
    ext['total_invoice_value'] = invoice_total
    ext['invoice_total'] = invoice_total
    ext['total_amount'] = invoice_total
    
    if 'sections' in ext and isinstance(ext['sections'], dict):
        supply_details = ext['sections'].setdefault('supply_details', {})
        if isinstance(supply_details, dict):
            supply_details['total_cgst'] = cgst
            supply_details['total_sgst'] = sgst
            supply_details['total_igst'] = igst
            supply_details['total_cess'] = cess
            supply_details['total_invoice_value'] = invoice_total
            supply_details['total_taxable_value'] = taxable_total
            
    if 'assembled_exports' in ext and isinstance(ext['assembled_exports'], list) and ext['assembled_exports']:
        ae = ext['assembled_exports'][0]
        if isinstance(ae, dict):
            ae['total_cgst'] = cgst
            ae['total_sgst'] = sgst
            ae['total_igst'] = igst
            ae['total_cess'] = cess
            ae['total_invoice_value'] = invoice_total
            ae['invoice_total'] = invoice_total
            ae['total_amount'] = invoice_total
            if 'sections' in ae and isinstance(ae['sections'], dict):
                ae_supply = ae['sections'].setdefault('supply_details', {})
                if isinstance(ae_supply, dict):
                    ae_supply['total_cgst'] = cgst
                    ae_supply['total_sgst'] = sgst
                    ae_supply['total_igst'] = igst
                    ae_supply['total_cess'] = cess
                    ae_supply['total_invoice_value'] = invoice_total
                    ae_supply['total_taxable_value'] = taxable_total

def restore_supplier_gst_values(record):
    """
    Restores original OCR item-level tax fields from _raw_extraction.items
    to canonical extracted_data.items using an order-preserving subsequence matcher,
    and recalculates header totals to ensure mathematical consistency.
    """
    ext = record.extracted_data or {}
    raw_items = ext.get('_raw_extraction', {}).get('items', [])
    items = ext.get('items', [])
    if not raw_items or not items:
        return
        
    raw_ptr = 0
    restored_cgst_total = 0.0
    restored_sgst_total = 0.0
    restored_igst_total = 0.0
    restored_cess_total = 0.0
    restored_taxable_total = 0.0
    
    for item in items:
        if not isinstance(item, dict): continue
        c_desc = str(item.get('description') or '').strip().lower()
        c_qty = float(item.get('qty') or 0.0)
        c_rate = float(item.get('rate') or 0.0)
        restored_taxable_total += float(item.get('taxable_value') or 0.0)
        
        raw_itm = None
        while raw_ptr < len(raw_items):
            raw = raw_items[raw_ptr]
            if not isinstance(raw, dict):
                raw_ptr += 1
                continue
            r_desc = str(raw.get('description') or raw.get('Item Name') or '').strip().lower()
            r_qty = float(raw.get('qty') or raw.get('quantity') or 0.0)
            r_rate = float(raw.get('rate') or raw.get('unit_price') or raw.get('Item Rate') or 0.0)
            
            is_desc_match = r_desc and (r_desc == c_desc or r_desc in c_desc)
            is_finance_match = abs(c_qty - r_qty) < 0.01 and abs(c_rate - r_rate) < 0.01
            
            if is_desc_match and is_finance_match:
                raw_itm = raw
                raw_ptr += 1
                break
            else:
                raw_ptr += 1
        
        if raw_itm:
            cgst_val = float(raw_itm.get('cgst') or raw_itm.get('cgst_amount') or 0.0)
            sgst_val = float(raw_itm.get('sgst') or raw_itm.get('sgst_amount') or 0.0)
            igst_val = float(raw_itm.get('igst') or raw_itm.get('igst_amount') or 0.0)
            cess_val = float(raw_itm.get('cess') or raw_itm.get('cess_amount') or 0.0)
            
            # Fallback: if amounts are zero but rates are non-zero, compute them.
            cgst_rate = float(raw_itm.get('cgst_rate') or raw_itm.get('cgst_pct') or item.get('cgst_rate') or 0.0)
            sgst_rate = float(raw_itm.get('sgst_rate') or raw_itm.get('sgst_pct') or item.get('sgst_rate') or 0.0)
            igst_rate = float(raw_itm.get('igst_rate') or raw_itm.get('igst_pct') or item.get('igst_rate') or 0.0)
            
            # Symmetric rate recovery for intrastate
            if igst_rate == 0.0:
                if cgst_rate == 0.0 and sgst_rate > 0.0:
                    cgst_rate = sgst_rate
                elif sgst_rate == 0.0 and cgst_rate > 0.0:
                    sgst_rate = cgst_rate
            
            taxable = float(item.get('taxable_value') or 0.0)
            
            if cgst_val == 0.0 and cgst_rate > 0.0:
                cgst_val = round(taxable * cgst_rate / 100.0, 2)
            if sgst_val == 0.0 and sgst_rate > 0.0:
                sgst_val = round(taxable * sgst_rate / 100.0, 2)
            if igst_val == 0.0 and igst_rate > 0.0:
                igst_val = round(taxable * igst_rate / 100.0, 2)
            
            item['cgst'] = cgst_val
            item['cgst_amount'] = str(cgst_val)
            item['sgst'] = sgst_val
            item['sgst_amount'] = str(sgst_val)
            item['igst'] = igst_val
            item['igst_amount'] = str(igst_val)
            item['cess'] = cess_val
            item['cess_amount'] = str(cess_val)
            
            restored_cgst_total += cgst_val
            restored_sgst_total += sgst_val
            restored_igst_total += igst_val
            restored_cess_total += cess_val
        else:
            logger.warning(
                f"[GST_RESTORATION_AMBIGUITY] record_id={record.id} "
                f"Could not match canonical item '{c_desc}' (qty={c_qty}, rate={c_rate}) to raw extraction items. Refusing restoration for this row."
            )
            
    # Apply and sync the recalculated totals
    restored_invoice_total = restored_taxable_total + restored_cgst_total + restored_sgst_total + restored_igst_total + restored_cess_total
    sync_nested_totals(
        ext, 
        restored_cgst_total, 
        restored_sgst_total, 
        restored_igst_total, 
        restored_cess_total, 
        restored_invoice_total, 
        restored_taxable_total
    )
