import React, { useState, useEffect } from 'react';
import { httpClient } from '../services/httpClient';
import { showError, showSuccess } from '../utils/toast';
import Icon from './Icon';

const round = (num: number, decimals: number = 2): number => {
    const factor = Math.pow(10, decimals);
    return Math.round((num + Number.EPSILON) * factor) / factor;
};

const getTaxVal = (item: any, key1: string, key2: string): number => {
    const val1 = item?.[key1];
    const val2 = item?.[key2];
    const num1 = val1 !== undefined && val1 !== null && val1 !== '' ? Number(val1) : NaN;
    const num2 = val2 !== undefined && val2 !== null && val2 !== '' ? Number(val2) : NaN;
    
    if (!isNaN(num1) && num1 !== 0) return num1;
    if (!isNaN(num2) && num2 !== 0) return num2;
    
    if (!isNaN(num1)) return num1;
    if (!isNaN(num2)) return num2;
    return 0;
};

/**
 * Returns the canonical discount percentage for an item,
 * checking all known key variants.  Returns 0 when no discount.
 */
const getItemDiscountPct = (item: any, rawItem?: any): number => {
    // Use explicit null/undefined checks so discount_percent = 0 is NOT skipped.
    let val = 0;
    if (item.discount_percent !== undefined && item.discount_percent !== null && Number(item.discount_percent) !== 0) {
        val = Number(item.discount_percent);
    } else if (item.discount_pct !== undefined && item.discount_pct !== null && Number(item.discount_pct) !== 0) {
        val = Number(item.discount_pct);
    } else if (item.discount_percentage !== undefined && item.discount_percentage !== null && Number(item.discount_percentage) !== 0) {
        val = Number(item.discount_percentage);
    } else if (item.discount_percent_extracted !== undefined && item.discount_percent_extracted !== null && Number(item.discount_percent_extracted) !== 0) {
        val = Number(item.discount_percent_extracted);
    } else if (rawItem) {
        if (rawItem.discount_percent !== undefined && rawItem.discount_percent !== null) val = Number(rawItem.discount_percent);
        else if (rawItem.discount_pct !== undefined && rawItem.discount_pct !== null) val = Number(rawItem.discount_pct);
        else if (rawItem.discount_percentage !== undefined && rawItem.discount_percentage !== null) val = Number(rawItem.discount_percentage);
        else if (rawItem.discount_percent_extracted !== undefined && rawItem.discount_percent_extracted !== null) val = Number(rawItem.discount_percent_extracted);
    }
    return val;
};

/**
 * Returns the canonical discount amount for an item.
 * Returns 0 when no discount.
 */
const getItemDiscountAmt = (item: any, rawItem?: any): number => {
    let val = 0;
    if (item.discount_amount !== undefined && item.discount_amount !== null && Number(item.discount_amount) !== 0) {
        val = Number(item.discount_amount);
    } else if (item.discount_value !== undefined && item.discount_value !== null && Number(item.discount_value) !== 0) {
        val = Number(item.discount_value);
    } else if (item.discount_extracted !== undefined && item.discount_extracted !== null && Number(item.discount_extracted) !== 0) {
        val = Number(item.discount_extracted);
    } else if (rawItem) {
        if (rawItem.discount_amount !== undefined && rawItem.discount_amount !== null) val = Number(rawItem.discount_amount);
        else if (rawItem.discount_value !== undefined && rawItem.discount_value !== null) val = Number(rawItem.discount_value);
        else if (rawItem.discount_extracted !== undefined && rawItem.discount_extracted !== null) val = Number(rawItem.discount_extracted);
    }
    return val;
};

const calculateItemTaxableValue = (item: any, rawItem?: any): number => {
    const qty  = Number(item.qty || item.quantity || 0);
    const rate = Number(item.rate || item.unit_price || item.itemRate || 0);

    const discPct = getItemDiscountPct(item, rawItem);
    const discAmt = getItemDiscountAmt(item, rawItem);

    // Rule 1 – If a discount is specified, compute from gross.
    if (discPct > 0) {
        return round((qty * rate) * (1 - discPct / 100), 2);
    }
    if (discAmt > 0) {
        return round((qty * rate) - discAmt, 2);
    }

    // Rule 2 – No discount: trust the backend-computed taxable_value directly.
    // The backend already ran calculate_item_taxable_value and stored the result.
    // Do NOT re-derive from GST amounts or estimate.
    const explicitTaxable =
        item.taxable_value !== undefined ? item.taxable_value :
        item.TaxableValue !== undefined ? item.TaxableValue :
        item.taxableValue !== undefined ? item.taxableValue : undefined;
    if (explicitTaxable !== undefined && explicitTaxable !== null && explicitTaxable !== '') {
        return Number(explicitTaxable);
    }

    // Rule 3 – Fall back to the line Amount (post-discount, pre-GST) if present.
    const amt = item.amount !== undefined ? item.amount : item.Amount;
    if (amt !== undefined && amt !== null && amt !== '') {
        return Number(amt);
    }

    // Rule 4 – Last resort: qty × rate (gross, no discount applied).
    return round(qty * rate, 2);
};

const getLineItems = (rec: any): any[] => {
    if (rec?.review_payload?.items) return rec.review_payload.items;
    const ext = rec?.extracted_data || rec?.extraction_payload || {};
    if (ext.items) return ext.items;
    if (ext.sections?.items) return ext.sections.items;
    if (ext.line_items) return ext.line_items;
    if (ext.assembled_exports && ext.assembled_exports[0]?.items) return ext.assembled_exports[0].items;
    if (ext.invoice?.items) return ext.invoice.items;
    return [];
};

export interface GstCorrectionModalProps {
    onClose: () => void;
    /** The staging record ID (maps to InvoiceTempOCR.id) */
    stagingId: string | number;
    /** The staging record or purchase object containing extracted_data / extraction_payload */
    record: any;
    /** Callback on successful save, receives the updated row payload */
    onSaveSuccess: (updatedRow: any) => void;
}

export const GstCorrectionModal: React.FC<GstCorrectionModalProps> = ({
    onClose,
    stagingId,
    record,
    onSaveSuccess,
}) => {
    // Determine the source of extraction data (varies between SmartInvoiceUploadModal and PendingPurchases)
    const extData = record.extracted_data || record.extraction_payload || {};
    const auditTrail = extData.gst_audit_trail || {};
    const expectedValues = auditTrail.expected_tax_values || {};
    const extractedValues = auditTrail.extracted_tax_values || {};
    const resolutionChoice = record.gst_resolution || extData.gst_resolution || auditTrail.resolution_choice || '';

    const initialCgst = Number(extractedValues.cgst || extData.total_cgst || extData.cgst || 0);
    const initialSgst = Number(extractedValues.sgst || extData.total_sgst || extData.sgst || 0);
    const initialIgst = Number(extractedValues.igst || extData.total_igst || extData.igst || 0);

    const [itemsState, setItemsState] = useState<any[]>([]);

    useEffect(() => {
        if (record) {
            const rawItems = getLineItems(record);
            const mapped = rawItems.map((item: any, idx: number) => {
                const rawItemsExtract = extData._raw_extraction?.items || extData._raw_extraction?.line_items || [];
                const rawItem = rawItemsExtract[idx];

                const qty = Number(item.qty || item.quantity || 0);
                const rate = Number(item.rate || item.unit_price || item.itemRate || 0);
                
                let discPct = getItemDiscountPct(item, rawItem);
                let discAmt = getItemDiscountAmt(item, rawItem);
                
                const taxable = calculateItemTaxableValue(item, rawItem);
                const grossAmt = round(qty * rate, 2);
                
                if (discPct === 0 && discAmt === 0 && grossAmt > 0 && taxable < grossAmt) {
                    discPct = round(((grossAmt - taxable) / grossAmt) * 100, 2);
                }

                const gstRate = Number(item.gst_rate || item.gstRate || item.tax_rate || item.computed_gst_rate || (Number(item.cgst_rate || 0) + Number(item.sgst_rate || 0) + Number(item.igst_rate || 0)) || 0);
                
                let currentCgst = getTaxVal(item, 'cgst_amount', 'cgst');
                let currentSgst = getTaxVal(item, 'sgst_amount', 'sgst');
                let currentIgst = getTaxVal(item, 'igst_amount', 'igst');
                
                if (currentCgst === 0 && currentSgst === 0 && currentIgst === 0 && rawItem) {
                    currentCgst = getTaxVal(rawItem, 'cgst_amount', 'cgst');
                    currentSgst = getTaxVal(rawItem, 'sgst_amount', 'sgst');
                    currentIgst = getTaxVal(rawItem, 'igst_amount', 'igst');
                }
                
                if (currentCgst === 0 && currentSgst === 0 && currentIgst === 0) {
                    let cgstRate = Number(item.cgst_rate || (rawItem && rawItem.cgst_rate) || 0);
                    let sgstRate = Number(item.sgst_rate || (rawItem && rawItem.sgst_rate) || 0);
                    let igstRate = Number(item.igst_rate || (rawItem && rawItem.igst_rate) || 0);
                    
                    if (igstRate === 0) {
                        if (cgstRate === 0 && sgstRate > 0) cgstRate = sgstRate;
                        else if (sgstRate === 0 && cgstRate > 0) cgstRate = cgstRate;
                    }
                    
                    if (cgstRate > 0) currentCgst = round(taxable * cgstRate / 100, 2);
                    if (sgstRate > 0) currentSgst = round(taxable * sgstRate / 100, 2);
                    if (igstRate > 0) currentIgst = round(taxable * igstRate / 100, 2);
                }

                let cgstRate = Number(item.cgst_rate || (rawItem && rawItem.cgst_rate) || 0);
                let sgstRate = Number(item.sgst_rate || (rawItem && rawItem.sgst_rate) || 0);
                let igstRate = Number(item.igst_rate || (rawItem && rawItem.igst_rate) || 0);
                
                if (igstRate === 0 && cgstRate === 0 && sgstRate === 0 && gstRate > 0) {
                    cgstRate = gstRate / 2;
                    sgstRate = gstRate / 2;
                }

                return {
                    ...item,
                    description: item.description || item.itemName || item.name || item.item_name || '—',
                    hsn_sac: item.hsn_sac || item.hsn_code || item.hsnSac || '—',
                    qty,
                    rate,
                    discount_percent: discPct,
                    discount_amount: discAmt,
                    taxable_value: taxable,
                    gst_rate: gstRate,
                    cgst_rate: cgstRate,
                    sgst_rate: sgstRate,
                    igst_rate: igstRate,
                    cgst: currentCgst,
                    sgst: currentSgst,
                    igst: currentIgst,
                };
            });
            setItemsState(mapped);
        }
    }, [record]);

    const recalculateGstRate = (item: any, totalGstRate: number) => {
        item.gst_rate = totalGstRate;
        const isInterstate = Number(item.igst_rate || extData.total_igst || 0) > 0;
        if (isInterstate) {
            item.igst_rate = totalGstRate;
            item.cgst_rate = 0;
            item.sgst_rate = 0;
            
            item.igst = round(item.taxable_value * totalGstRate / 100, 2);
            item.cgst = 0;
            item.sgst = 0;
        } else {
            item.cgst_rate = totalGstRate / 2;
            item.sgst_rate = totalGstRate / 2;
            item.igst_rate = 0;
            
            item.cgst = round(item.taxable_value * (totalGstRate / 2) / 100, 2);
            item.sgst = round(item.taxable_value * (totalGstRate / 2) / 100, 2);
            item.igst = 0;
        }
        return item;
    };

    const recalculateItemRow = (item: any) => {
        const qty = Number(item.qty || 0);
        const rate = Number(item.rate || 0);
        const discPct = Number(item.discount_percent || 0);
        const discAmt = Number(item.discount_amount || 0);
        
        const gross = qty * rate;
        let discount = 0;
        if (discPct > 0) {
            discount = gross * (discPct / 100);
        } else if (discAmt > 0) {
            discount = discAmt;
        }
        
        item.taxable_value = round(gross - discount, 2);
        return recalculateGstRate(item, Number(item.gst_rate || 0));
    };

    const updateField = (idx: number, field: string, value: any) => {
        const updated = [...itemsState];
        const item = { ...updated[idx], [field]: value };
        
        if (field === 'qty' || field === 'rate' || field === 'discount_percent' || field === 'discount_amount') {
            updated[idx] = recalculateItemRow(item);
        } else if (field === 'gst_rate') {
            updated[idx] = recalculateGstRate(item, Number(value));
        } else if (field === 'taxable_value') {
            item.taxable_value = Number(value);
            updated[idx] = recalculateGstRate(item, Number(item.gst_rate || 0));
        } else {
            updated[idx] = item;
        }
        setItemsState(updated);
    };

    const handleDiscountChange = (idx: number, val: string) => {
        const updated = [...itemsState];
        const item = { ...updated[idx] };
        
        const cleanVal = val.trim();
        if (cleanVal.endsWith('%')) {
            const pct = Number(cleanVal.slice(0, -1)) || 0;
            item.discount_percent = pct;
            item.discount_amount = 0;
        } else {
            const amt = Number(cleanVal.replace(/[₹,]/g, '')) || 0;
            item.discount_amount = amt;
            item.discount_percent = 0;
        }
        
        updated[idx] = recalculateItemRow(item);
        setItemsState(updated);
    };

    const handleCurrentGstChange = (idx: number, gstVal: number) => {
        const updated = [...itemsState];
        const item = { ...updated[idx] };
        
        const isInterstate = Number(item.igst_rate || extData.total_igst || 0) > 0;
        if (isInterstate) {
            item.igst = gstVal;
            item.cgst = 0;
            item.sgst = 0;
        } else {
            item.cgst = gstVal / 2;
            item.sgst = gstVal / 2;
            item.igst = 0;
        }
        
        updated[idx] = item;
        setItemsState(updated);
    };

    // Editable form state
    const [cgst, setCgst] = useState<string>(initialCgst.toFixed(2));
    const [sgst, setSgst] = useState<string>(initialSgst.toFixed(2));
    const [igst, setIgst] = useState<string>(initialIgst.toFixed(2));
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        let sumCgst = 0;
        let sumSgst = 0;
        let sumIgst = 0;
        
        itemsState.forEach((item) => {
            sumCgst += Number(item.cgst || 0);
            sumSgst += Number(item.sgst || 0);
            sumIgst += Number(item.igst || 0);
        });
        
        setCgst(sumCgst.toFixed(2));
        setSgst(sumSgst.toFixed(2));
        setIgst(sumIgst.toFixed(2));
    }, [itemsState]);

    const cgstVal = Number(cgst) || 0;
    const sgstVal = Number(sgst) || 0;
    const igstVal = Number(igst) || 0;

    const liveTotalGst = cgstVal + sgstVal + igstVal;

    // Dynamically compute expected total, taxable total, and gst rates
    let expectedTotalGst = 0;
    let taxableValue = 0;
    let expectedCgstSum = 0;
    let expectedSgstSum = 0;
    let expectedIgstSum = 0;

    itemsState.forEach((item) => {
        taxableValue += Number(item.taxable_value || 0);
        const expectedCgst = round(Number(item.taxable_value || 0) * Number(item.cgst_rate || 0) / 100, 2);
        const expectedSgst = round(Number(item.taxable_value || 0) * Number(item.sgst_rate || 0) / 100, 2);
        const expectedIgst = round(Number(item.taxable_value || 0) * Number(item.igst_rate || 0) / 100, 2);
        
        expectedCgstSum += expectedCgst;
        expectedSgstSum += expectedSgst;
        expectedIgstSum += expectedIgst;
        expectedTotalGst += expectedCgst + expectedSgst + expectedIgst;
    });

    const liveDifference = Math.abs(expectedTotalGst - liveTotalGst);
    const isWithinTolerance = liveDifference <= 1.0;
    const gstRate = extData.gst_rate || '—';

    const handleSave = async (chosenResolution: 'CORRECTED' | 'SUPPLIER_VALUES_ACCEPTED') => {
        if (!stagingId) {
            showError('Invalid record ID. Cannot perform GST correction.');
            return;
        }

        setSubmitting(true);
        try {
            const result = await httpClient.post<any>(
                `/api/ocr-staging/${stagingId}/correct-gst/`,
                {
                    cgst: chosenResolution === 'CORRECTED' ? cgstVal : initialCgst,
                    sgst: chosenResolution === 'CORRECTED' ? sgstVal : initialSgst,
                    igst: chosenResolution === 'CORRECTED' ? igstVal : initialIgst,
                    resolution: chosenResolution,
                    items: itemsState
                }
            );

            const updatedRow = result; // Response is the updated staging row payload
            const newAuditTrail = (updatedRow.extracted_data || updatedRow.extraction_payload || {}).gst_audit_trail || {};
            const newDiff = Number(newAuditTrail.difference_amount || 0);

            if (chosenResolution === 'SUPPLIER_VALUES_ACCEPTED') {
                showSuccess('Original OCR extracted GST values preserved!');
            } else if (newDiff <= 1.0) {
                showSuccess('GST mismatch corrected successfully! Status updated to VALID/NEED_TO_SAVE.');
            } else {
                showSuccess(`GST values updated, but difference of ₹${newDiff.toFixed(2)} still exceeds tolerance limit.`);
            }

            onSaveSuccess(updatedRow);
            onClose();
        } catch (err: any) {
            console.error('[GST_CORRECTION_MODAL] Correction failed:', err);
            showError(err?.response?.data?.error || err?.response?.data?.message || 'Failed to update GST values.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div
            id="gst-correction-modal-overlay"
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 transition-opacity duration-300 animate-in fade-in duration-150"
        >
            <div className="bg-white border border-gray-200 text-gray-800 rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col transform transition-all duration-300 scale-100 max-h-[90vh]">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 bg-rose-50/30 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center text-rose-600">
                            <Icon name="edit" className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="font-extrabold text-lg tracking-wide text-gray-800">
                                Correct GST Mismatch
                            </h3>
                            <p className="text-xs text-gray-500 font-medium">
                                Adjust tax values to resolve invoice validation discrepancy
                            </p>
                        </div>
                    </div>
                    <button
                        id="gst-correction-modal-close"
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-colors cursor-pointer"
                    >
                        <Icon name="close" className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 flex-1 overflow-y-auto space-y-6">
                    {/* Summary Card */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 border border-slate-200/80 rounded-xl shadow-sm">
                        <div>
                            <span className="block text-[10px] uppercase font-bold text-gray-400 tracking-wider">Taxable Value</span>
                            <span className="text-sm font-extrabold text-gray-700">₹{taxableValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                        <div>
                            <span className="block text-[10px] uppercase font-bold text-gray-400 tracking-wider">Expected Tax</span>
                            <span className="text-sm font-extrabold text-gray-700">₹{expectedTotalGst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                        <div>
                            <span className="block text-[10px] uppercase font-bold text-gray-400 tracking-wider">Current Tax</span>
                            <span className="text-sm font-extrabold text-gray-700">₹{liveTotalGst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                    </div>

                    {/* Item-wise GST Breakdown Table */}
                    {itemsState && itemsState.length > 0 && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                            <div className="bg-slate-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                                <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Item-wise GST Breakdown</h4>
                                <span className="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-bold">
                                    {itemsState.length} {itemsState.length === 1 ? 'Item' : 'Items'}
                                </span>
                            </div>
                            <div className="overflow-x-auto max-h-[300px]">
                                <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                                    <thead className="bg-slate-100 sticky top-0 backdrop-blur-sm z-10 font-bold text-gray-500 uppercase tracking-wider">
                                        <tr>
                                            <th className="px-4 py-2 text-[10px]">Item Name</th>
                                            <th className="px-4 py-2 text-[10px]">HSN/SAC</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Qty</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Rate</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Discount</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Taxable Value</th>
                                            <th className="px-4 py-2 text-[10px] text-center">GST Rate</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Expected GST</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Current GST</th>
                                            <th className="px-4 py-2 text-[10px] text-right">Difference</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-100">
                                        {itemsState.map((item: any, idx: number) => {
                                            const itemName = item.description || '—';
                                            const hsnSac = item.hsn_sac || '—';
                                            const qty = Number(item.qty || 0);
                                            const rate = Number(item.rate || 0);
                                            const taxable = Number(item.taxable_value || 0);
                                            const grossAmt = round(qty * rate, 2);
                                            
                                            const gstRateVal = Number(item.gst_rate || 0);
                                            const expectedGst = round(taxable * gstRateVal / 100, 2);
                                            
                                            const currentCgst = Number(item.cgst || 0);
                                            const currentSgst = Number(item.sgst || 0);
                                            const currentIgst = Number(item.igst || 0);
                                            const currentGst = currentCgst + currentSgst + currentIgst;
                                            
                                            const diff = Math.abs(expectedGst - currentGst);
                                            
                                            return (
                                                <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-2 py-1.5 font-medium text-gray-900 max-w-[150px]">
                                                        <input
                                                            type="text"
                                                            className="w-full bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs"
                                                            value={item.description || ''}
                                                            onChange={(e) => updateField(idx, 'description', e.target.value)}
                                                        />
                                                    </td>
                                                    <td className="px-2 py-1.5 text-gray-500">
                                                        <input
                                                            type="text"
                                                            className="w-16 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-center"
                                                            value={item.hsn_sac || ''}
                                                            onChange={(e) => updateField(idx, 'hsn_sac', e.target.value)}
                                                        />
                                                    </td>
                                                    <td className="px-2 py-1.5 text-right font-medium text-gray-700">
                                                        <input
                                                            type="number"
                                                            className="w-12 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-right"
                                                            value={item.qty === 0 ? '' : item.qty}
                                                            onChange={(e) => updateField(idx, 'qty', Number(e.target.value))}
                                                        />
                                                    </td>
                                                    <td className="px-2 py-1.5 text-right font-medium text-gray-700">
                                                        <div className="flex items-center justify-end gap-0.5">
                                                            <span className="text-[10px] text-gray-400">₹</span>
                                                            <input
                                                                type="number"
                                                                step="0.01"
                                                                className="w-20 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-right"
                                                                value={item.rate === 0 ? '' : item.rate}
                                                                onChange={(e) => updateField(idx, 'rate', Number(e.target.value))}
                                                            />
                                                        </div>
                                                    </td>
                                                    <td className="px-2 py-1.5 text-right font-semibold text-rose-600">
                                                        <input
                                                            type="text"
                                                            className="w-16 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-center font-bold text-rose-600"
                                                            value={item.discount_percent > 0 ? `${item.discount_percent}%` : item.discount_amount > 0 ? `${item.discount_amount}` : ''}
                                                            placeholder="—"
                                                            onChange={(e) => handleDiscountChange(idx, e.target.value)}
                                                        />
                                                    </td>
                                                    <td className="px-2 py-1.5 text-right font-bold text-gray-800">
                                                        <div className="flex items-center justify-end gap-0.5">
                                                            <span className="text-[10px] text-gray-400">₹</span>
                                                            <input
                                                                type="number"
                                                                step="0.01"
                                                                className="w-20 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-right font-bold"
                                                                value={item.taxable_value === 0 ? '' : item.taxable_value}
                                                                onChange={(e) => updateField(idx, 'taxable_value', Number(e.target.value))}
                                                            />
                                                        </div>
                                                    </td>
                                                    <td className="px-2 py-1.5 text-center font-semibold text-gray-700">
                                                        <div className="flex items-center justify-center gap-0.5">
                                                            <input
                                                                type="number"
                                                                className="w-10 bg-transparent focus:bg-white px-1 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-center"
                                                                value={item.gst_rate === 0 ? '' : item.gst_rate}
                                                                onChange={(e) => updateField(idx, 'gst_rate', Number(e.target.value))}
                                                            />
                                                            <span className="text-[10px] text-gray-400">%</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-bold text-emerald-600">₹{expectedGst.toFixed(2)}</td>
                                                    <td className="px-2 py-1.5 text-right font-semibold text-gray-700">
                                                        <div className="flex items-center justify-end gap-0.5">
                                                            <span className="text-[10px] text-gray-400">₹</span>
                                                            <input
                                                                type="number"
                                                                step="0.01"
                                                                className="w-18 bg-transparent focus:bg-white px-1.5 py-0.5 border border-transparent hover:border-gray-200 focus:border-indigo-500 rounded text-xs text-right font-semibold"
                                                                value={currentGst === 0 ? '' : currentGst.toFixed(2)}
                                                                onChange={(e) => handleCurrentGstChange(idx, Number(e.target.value))}
                                                            />
                                                        </div>
                                                    </td>
                                                    <td className={`px-4 py-2.5 text-right font-black ${diff > 0.01 ? 'text-rose-600' : 'text-gray-400'}`}>
                                                        ₹{diff.toFixed(2)}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Main correction columns */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Expected Values Panel */}
                        <div className="md:col-span-1 border border-slate-100 rounded-xl p-4 bg-slate-50/40 space-y-4">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider border-b pb-2">Expected (Calculated)</h4>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">Expected CGST:</span>
                                    <span className="font-bold text-gray-800">₹{expectedCgstSum.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">Expected SGST:</span>
                                    <span className="font-bold text-gray-800">₹{expectedSgstSum.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">Expected IGST:</span>
                                    <span className="font-bold text-gray-800">₹{expectedIgstSum.toFixed(2)}</span>
                                </div>
                                <div className="pt-2 border-t flex justify-between items-center text-xs">
                                    <span className="font-semibold text-gray-500">Expected Total:</span>
                                    <span className="font-black text-emerald-600">₹{expectedTotalGst.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Editable Form Inputs */}
                        <div className="md:col-span-2 space-y-4">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider border-b pb-2">Enter Corrected Values</h4>
                            
                            <div className="grid grid-cols-3 gap-4">
                                <div className="space-y-1">
                                    <label htmlFor="cgst-input" className="block text-xs font-semibold text-gray-600">CGST Amount (₹)</label>
                                    <input
                                        id="cgst-input"
                                        type="number"
                                        step="0.01"
                                        value={cgst}
                                        onChange={(e) => setCgst(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label htmlFor="sgst-input" className="block text-xs font-semibold text-gray-600">SGST Amount (₹)</label>
                                    <input
                                        id="sgst-input"
                                        type="number"
                                        step="0.01"
                                        value={sgst}
                                        onChange={(e) => setSgst(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label htmlFor="igst-input" className="block text-xs font-semibold text-gray-600">IGST Amount (₹)</label>
                                    <input
                                        id="igst-input"
                                        type="number"
                                        step="0.01"
                                        value={igst}
                                        onChange={(e) => setIgst(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
                                    />
                                </div>
                            </div>

                            {/* Live calculations */}
                            <div className="p-4 bg-slate-50 border border-slate-200/60 rounded-xl space-y-2.5 text-xs">
                                <div className="flex justify-between text-gray-500">
                                    <span>Calculated Expected Total GST:</span>
                                    <span className="font-bold text-gray-800">₹{expectedTotalGst.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-gray-500">
                                    <span>Entered Corrected Total GST:</span>
                                    <span className="font-bold text-gray-800">₹{liveTotalGst.toFixed(2)}</span>
                                </div>
                                <div className="border-t pt-2 flex justify-between items-center">
                                    <span className="font-semibold text-gray-600">Calculated Difference:</span>
                                    <span className={`font-black text-sm ${isWithinTolerance ? 'text-emerald-600' : 'text-rose-600 animate-pulse'}`}>
                                        ₹{liveDifference.toFixed(2)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Interactive validation warning/helper info */}
                    <div className={`p-4 border rounded-xl flex items-start gap-3 text-xs leading-relaxed shadow-sm transition-all duration-300 ${
                        isWithinTolerance 
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                            : 'bg-rose-50 border-rose-200 text-rose-800'
                    }`}>
                        <div className={`p-1.5 rounded-lg ${isWithinTolerance ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                            <Icon name={isWithinTolerance ? 'check' : 'warning'} className="w-4 h-4" />
                        </div>
                        <div>
                            {isWithinTolerance ? (
                                <>
                                    <span className="font-extrabold block mb-0.5 text-emerald-900">Difference within tolerance limit (₹1.00)</span>
                                    The entered values match the calculated expected tax values within the allowable limit. Upon saving, the invoice GST status will resolve to <strong>VALID</strong>.
                                </>
                            ) : (
                                <>
                                    <span className="font-extrabold block mb-0.5 text-rose-900">Difference exceeds tolerance limit (₹1.00)</span>
                                    The difference (₹{liveDifference.toFixed(2)}) is still outside the allowable tolerance limit. Saving these values will update the staging record but will keep the invoice in <strong>GST MISMATCH</strong> status.
                                </>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-slate-50 border-t border-gray-200 flex items-center justify-end gap-3 flex-shrink-0">
                    <button
                        id="gst-correction-modal-cancel"
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 text-xs font-semibold rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none transition-colors cursor-pointer disabled:opacity-50"
                        disabled={submitting}
                    >
                        Cancel
                    </button>
                    <button
                        id="gst-correction-modal-save-extracted"
                        onClick={() => handleSave('SUPPLIER_VALUES_ACCEPTED')}
                        disabled={submitting}
                        className={`inline-flex items-center justify-center px-4 py-2 text-xs font-bold rounded-lg focus:outline-none transition-all flex items-center gap-1.5 cursor-pointer border ${
                            resolutionChoice === 'SUPPLIER_VALUES_ACCEPTED'
                                ? 'bg-indigo-50 border-indigo-300 text-indigo-700 hover:bg-indigo-100'
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                    >
                        {submitting && resolutionChoice === 'SUPPLIER_VALUES_ACCEPTED' ? (
                            <>
                                <Icon name="spinner" className="w-3.5 h-3.5 animate-spin" />
                                Saving Current GST...
                            </>
                        ) : (
                            <>
                                {resolutionChoice === 'SUPPLIER_VALUES_ACCEPTED' && <Icon name="check" className="w-3.5 h-3.5" />}
                                Save Current GST
                            </>
                        )}
                    </button>
                    <button
                        id="gst-correction-submit"
                        onClick={() => handleSave('CORRECTED')}
                        disabled={submitting}
                        className={`inline-flex items-center justify-center px-5 py-2 text-xs font-bold rounded-lg focus:outline-none shadow-sm transition-all flex items-center gap-2 cursor-pointer border ${
                            resolutionChoice === 'CORRECTED' || !resolutionChoice
                                ? 'bg-rose-600 border-rose-700 text-white hover:bg-rose-700'
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                    >
                        {submitting && (resolutionChoice === 'CORRECTED' || !resolutionChoice) ? (
                            <>
                                <Icon name="spinner" className="w-4 h-4 animate-spin" />
                                Saving Expected GST...
                            </>
                        ) : (
                            <>
                                {(resolutionChoice === 'CORRECTED' || !resolutionChoice) && <Icon name="check" className="w-4 h-4" />}
                                Save Expected GST
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};
