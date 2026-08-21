import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';
import { apiService } from '../../services/api';
import { showSuccess, showError } from '../../utils/toast';
import { getXLSX } from '../../utils/xlsx';

export default function GSTR2Reconciliation({ onNavigate, setViewVoucherData, refreshKey }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void, refreshKey?: number }) {
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [selectedRow, setSelectedRow] = useState<any>(null);
    const [summary, setSummary] = useState<any>({
        exact_match: 0,
        partial_match: 0,
        missing_in_books: 0,
        missing_in_2b: 0
    });
    
    const [selectedMonth, setSelectedMonth] = useState('January');
    const [selectedYear, setSelectedYear] = useState('2024-25');

    // Exact match bulk selection & push state
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [showPushConfirmModal, setShowPushConfirmModal] = useState(false);
    const [isPushing, setIsPushing] = useState(false);

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const years = ['2023-24', '2024-25', '2025-26', '2026-27'];

    const fetchResults = async () => {
        setIsLoading(true);
        try {
            const res = await apiService.fetchGSTR2BResults(selectedMonth, selectedYear);
            if (res) {
                setResults(res.results || []);
                if (res.summary) {
                    setSummary(res.summary);
                }
            }
        } catch (e: any) {
            console.error('Failed to fetch results', e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        setSelectedIds([]);
        fetchResults();
    }, [selectedMonth, selectedYear]);

    // Exact Match Selection calculations
    const exactRows = results.filter(r => r.status === 'EXACT');
    const selectedExactRows = exactRows.filter(r => selectedIds.includes(r.id));
    const selectedCount = selectedExactRows.length;
    const isAllExactSelected = exactRows.length > 0 && selectedExactRows.length === exactRows.length;

    const toggleSelectAllExact = () => {
        if (isAllExactSelected) {
            setSelectedIds([]);
        } else {
            setSelectedIds(exactRows.map(r => r.id));
        }
    };

    const toggleSelectRow = (id: number) => {
        setSelectedIds(prev =>
            prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
        );
    };

    // Calculation for confirmation modal
    const eligibleInvoices = selectedExactRows.filter(r => (
        r.itc_availability === 'YES' ||
        r.itc_availment === 'YES' ||
        String(r.raw_data?.itcavl || '').toUpperCase() !== 'N'
    ));

    const totalEligibleIGST = eligibleInvoices.reduce((sum, r) => sum + (Number(r.igst) || 0), 0);
    const totalEligibleCGST = eligibleInvoices.reduce((sum, r) => sum + (Number(r.cgst) || 0), 0);
    const totalEligibleSGST = eligibleInvoices.reduce((sum, r) => sum + (Number(r.sgst) || 0), 0);
    const totalEligibleCESS = eligibleInvoices.reduce((sum, r) => sum + (Number(r.cess) || 0), 0);
    const totalEligibleITC = totalEligibleIGST + totalEligibleCGST + totalEligibleSGST + totalEligibleCESS;

    const handlePushToGSTR3B = async () => {
        if (selectedExactRows.length === 0) return;
        setIsPushing(true);
        try {
            const res: any = await httpClient.post('/api/gst/reconciliation/push_to_gstr3b/', {
                month: selectedMonth,
                year: selectedYear,
                reconciliation_ids: selectedExactRows.map(r => r.id)
            });
            showSuccess(res.message || `${res.pushed_count || selectedExactRows.length} invoices successfully pushed to GSTR-3B!`);
            setShowPushConfirmModal(false);
            setSelectedIds([]);
            await fetchResults();
        } catch (err: any) {
            showError(err.response?.data?.error || err.message || 'Failed to push to GSTR-3B.');
        } finally {
            setIsPushing(false);
        }
    };

    // Auto-re-run reconciliation + fetch whenever user navigates back to this tab (refreshKey bumped)
    useEffect(() => {
        if (refreshKey === undefined || refreshKey === 0) return;
        const autoRefresh = async () => {
            setIsLoading(true);
            try {
                await httpClient.post('/api/gst/reconciliation/run_reconciliation/', { month: selectedMonth, year: selectedYear });
                await new Promise(r => setTimeout(r, 1800));
                await fetchResults();
            } catch (e) {
                // fallback: just refetch without re-running
                try { await fetchResults(); } catch (_) {}
            } finally {
                setIsLoading(false);
            }
        };
        autoRefresh();
    }, [refreshKey]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        try {
            const reader = new FileReader();
            reader.onload = async (event) => {
                const text = event.target?.result as string;
                try {
                    const json = JSON.parse(text);
                    const res: any = await httpClient.post('/api/gst/reconciliation/upload_2b/', json);
                    showSuccess(`GSTR-2B Ingested: ${res.created || 0} created, ${res.duplicates || 0} duplicate(s)`);
                    await httpClient.post('/api/gst/reconciliation/run_reconciliation/', { month: selectedMonth, year: selectedYear });
                    await new Promise(r => setTimeout(r, 1500));
                    await fetchResults();
                } catch (err: any) {
                    showError(err?.response?.data?.error || err.message || 'Invalid or unsupported GSTR-2B JSON file');
                } finally {
                    setIsLoading(false);
                }
            };
            reader.readAsText(file);
        } catch (err: any) {
            setIsLoading(false);
            showError('Failed to read file: ' + (err.message || 'Error'));
        } finally {
            if (e.target) e.target.value = '';
        }
    };

    const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        try {
            const XLSX = await getXLSX();
            const data = await file.arrayBuffer();
            const workbook = XLSX.read(data, { type: 'array', cellDates: true });

            const invoices: any[] = [];

            // Helper to clean and find header key in a row
            const findKey = (row: any, patterns: string[]) => {
                const keys = Object.keys(row);
                for (const p of patterns) {
                    const found = keys.find(k => k.toLowerCase().replace(/[^a-z0-9]/g, '').includes(p));
                    if (found && row[found] !== undefined && row[found] !== null && String(row[found]).trim() !== '') {
                        return row[found];
                    }
                }
                return '';
            };

            const parseNum = (val: any) => {
                if (val === undefined || val === null || val === '') return 0;
                const clean = String(val).replace(/[^0-9.-]/g, '');
                return parseFloat(clean) || 0;
            };

            workbook.SheetNames.forEach(sheetName => {
                const sheet = workbook.Sheets[sheetName];
                const rows: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false });

                rows.forEach(row => {
                    const gstin = String(findKey(row, ['gstin', 'ctin', 'uin'])).trim().toUpperCase();
                    const vendorName = String(findKey(row, ['tradename', 'legalname', 'suppliername', 'vendorname', 'partyname', 'tradelegalname', 'name'])).trim();
                    const invoiceNo = String(findKey(row, ['invoicenumber', 'invoiceno', 'docno', 'documentnumber', 'inum', 'invno', 'billno', 'ntnum'])).trim();

                    if (!gstin && !invoiceNo) return; // Skip non-invoice / blank rows

                    let invoiceDate = findKey(row, ['invoicedate', 'docdate', 'documentdate', 'date', 'idt', 'ntdt']);
                    if (invoiceDate instanceof Date) {
                        invoiceDate = invoiceDate.toISOString().split('T')[0];
                    } else if (typeof invoiceDate === 'string' && invoiceDate.trim()) {
                        invoiceDate = invoiceDate.trim();
                    } else {
                        invoiceDate = new Date().toISOString().split('T')[0];
                    }

                    const invoiceVal = parseNum(findKey(row, ['invoicevalue', 'totalamount', 'invoiceamt', 'invval', 'totalval', 'val']));
                    const taxableVal = parseNum(findKey(row, ['taxablevalue', 'taxableamt', 'txval', 'taxable']));
                    const igst = parseNum(findKey(row, ['integratedtax', 'igst', 'iamt']));
                    const cgst = parseNum(findKey(row, ['centraltax', 'cgst', 'camt']));
                    const sgst = parseNum(findKey(row, ['stateuttax', 'statetax', 'sgst', 'samt', 'uttax']));
                    const cess = parseNum(findKey(row, ['cessamount', 'cess', 'csamt']));

                    const rchrg = findKey(row, ['reversecharge', 'rchrg', 'rcm', 'isreversecharge', 'rev']) || 'N';
                    const itcAvl = findKey(row, ['itcavailability', 'itcavailment', 'itcavl', 'itceligible', 'itc', 'itcavailable', 'itceligibility']) || 'Y';
                    const period = findKey(row, ['filingperiod', 'gstr2bperiod', 'returnperiod', 'period', 'fp', 'month']) || '';

                    invoices.push({
                        gstin,
                        vendor_name: vendorName,
                        invoice_no: invoiceNo,
                        invoice_date: invoiceDate,
                        invoice_value: invoiceVal || (taxableVal + igst + cgst + sgst + cess),
                        taxable_value: taxableVal,
                        igst,
                        cgst,
                        sgst,
                        cess,
                        raw_data: {
                            ...row,
                            fp: period || row['Filing Period'] || row['fp'] || '',
                            rchrg: rchrg || row['Reverse Charge'] || row['rchrg'] || 'N',
                            itcavl: itcAvl || row['ITC Eligible'] || row['itcavl'] || 'Y'
                        }
                    });
                });
            });

            if (invoices.length === 0) {
                showError('No valid invoice rows found in the uploaded Excel file. Please ensure columns include GSTIN, Invoice No, Date, etc.');
                return;
            }

            const res: any = await httpClient.post('/api/gst/reconciliation/upload_2b/', invoices);
            showSuccess(`Excel Ingested: ${res.created || 0} created, ${res.duplicates || 0} duplicate(s)`);
            await httpClient.post('/api/gst/reconciliation/run_reconciliation/', { month: selectedMonth, year: selectedYear });
            await new Promise(r => setTimeout(r, 1500));
            await fetchResults();
        } catch (err: any) {
            console.error('Failed to parse and upload Excel file:', err);
            showError(err?.response?.data?.error || err.message || 'Failed to process Excel file');
        } finally {
            setIsLoading(false);
            if (e.target) e.target.value = '';
        }
    };

    const runReconciliation = async () => {
        setIsLoading(true);
        try {
            await httpClient.post('/api/gst/reconciliation/run_reconciliation/', { month: selectedMonth, year: selectedYear });
            showSuccess('Reconciliation process completed');
            await new Promise(r => setTimeout(r, 1500)); // Wait for background thread
            await fetchResults(); // Refresh table after running reco
        } finally {
            setIsLoading(false);
        }
    };

    const handleFetchFromSandbox = async () => {
        setIsLoading(true);
        try {
            // Fetch directly via Sandbox API (Mocked in backend)
            const res = await apiService.fetchGSTR2BSandbox(selectedMonth, selectedYear);
            if (res?.data?.b2b) {
                // Ingest the fetched data into our system
                await httpClient.post('/api/gst/reconciliation/upload_2b/', res.data.b2b);
                // Also trigger reconciliation automatically so the user sees results immediately
                await httpClient.post('/api/gst/reconciliation/run_reconciliation/', { month: selectedMonth, year: selectedYear });
                showSuccess('GSTR-2B data fetched and reconciled successfully!');
                await new Promise(r => setTimeout(r, 1500)); // Wait for background thread
                await fetchResults(); // Refresh table after ingestion & reco
            }
        } catch (e: any) {
            showError('Failed to fetch from Sandbox API: ' + (e.message || 'Error'));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="erp-container">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="section-title border-none pb-0">GSTR-2B Reconciliation Dashboard</h2>
                        <p className="helper-text mb-4">Match government data with your purchase books</p>
                        <div className="flex gap-4 items-center bg-indigo-50/50 p-2 rounded border border-indigo-100">
                            <span className="text-sm font-semibold text-indigo-900">Period:</span>
                            <select 
                                value={selectedMonth} 
                                onChange={(e) => setSelectedMonth(e.target.value)}
                                className="px-3 py-1.5 border border-indigo-200 rounded text-sm bg-white focus:ring-1 focus:ring-indigo-500"
                            >
                                {months.map(m => <option key={m} value={m}>{m}</option>)}
                            </select>
                            <select 
                                value={selectedYear} 
                                onChange={(e) => setSelectedYear(e.target.value)}
                                className="px-3 py-1.5 border border-indigo-200 rounded text-sm bg-white focus:ring-1 focus:ring-indigo-500"
                            >
                                {years.map(y => <option key={y} value={y}>{y}</option>)}
                            </select>
                        </div>
                    </div>
                    <div className="flex gap-3 self-start">
                        <button onClick={handleFetchFromSandbox} className="erp-button-secondary bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100" disabled={isLoading}>
                            ⚡ Fetch from Sandbox API
                        </button>
                        <label className="erp-button-secondary cursor-pointer self-center">
                            Upload JSON
                            <input type="file" className="hidden" onChange={handleUpload} accept=".json" />
                        </label>
                        <label className="erp-button-secondary cursor-pointer self-center bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100">
                            Upload Excel
                            <input type="file" className="hidden" onChange={handleExcelUpload} accept=".xlsx,.xls,.csv" />
                        </label>
                        <button onClick={runReconciliation} className="erp-button-primary" disabled={isLoading}>
                            {isLoading ? 'Processing...' : 'Run Reconciliation'}
                        </button>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 mt-4">
                    <div className="p-4 bg-emerald-50 rounded-[4px] border border-emerald-100">
                        <span className="text-sm text-emerald-700 font-medium">Exact Match</span>
                        <div className="text-2xl font-bold text-emerald-900">{summary.exact_match}</div>
                    </div>
                    <div className="p-4 bg-indigo-50 rounded-[4px] border border-indigo-100">
                        <span className="text-sm text-indigo-700 font-medium">Partial / Mismatch</span>
                        <div className="text-2xl font-bold text-indigo-900">{(summary.partial_match || 0) + (summary.mismatch || 0)}</div>
                    </div>
                    <div className="p-4 bg-rose-50 rounded-[4px] border border-rose-100">
                        <span className="text-sm text-rose-700 font-medium">Missing in Books</span>
                        <div className="text-2xl font-bold text-rose-900">{summary.missing_in_books}</div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-[4px] border border-slate-100">
                        <span className="text-sm text-slate-700 font-medium">Missing in 2B</span>
                        <div className="text-2xl font-bold text-slate-900">{summary.missing_in_2b}</div>
                    </div>
                </div>

                <div className="flex justify-between items-center mb-3">
                    <h3 className="text-sm font-semibold text-gray-700">Currently viewing GSTR-2B data for: {selectedMonth} {selectedYear}</h3>
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-semibold px-3 py-1.5 bg-slate-100 text-slate-700 rounded border border-slate-200">
                            {selectedCount} Exact Matches Selected
                        </span>
                        <button
                            onClick={() => setShowPushConfirmModal(true)}
                            disabled={selectedCount === 0 || isPushing}
                            className={`px-4 py-1.5 rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 ${
                                selectedCount > 0 && !isPushing
                                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer'
                                    : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                            }`}
                        >
                            🚀 PUSH TO GSTR-3B
                        </button>
                    </div>
                </div>
                <div className="erp-table-container">
                    <table className="erp-table">
                        <thead>
                            <tr>
                                <th 
                                    className="w-12 text-center cursor-pointer"
                                    onClick={(e) => {
                                        if (exactRows.length === 0) {
                                            e.stopPropagation();
                                            showError("No EXACT MATCH invoices available to select in the current period.");
                                        }
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={isAllExactSelected}
                                        onChange={toggleSelectAllExact}
                                        disabled={exactRows.length === 0}
                                        className={`rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4 ${exactRows.length > 0 ? 'cursor-pointer' : 'cursor-not-allowed opacity-40'}`}
                                        title={exactRows.length > 0 ? "Select All Exact Matches" : "No EXACT MATCH invoices to select"}
                                    />
                                </th>
                                <th>Status</th>
                                <th>Supplier GSTIN</th>
                                <th>Invoice No (2B)</th>
                                <th>Date (2B)</th>
                                <th>Value (2B)</th>
                                <th>Match %</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-10 text-slate-400">
                                        No reconciliation data found. Click "Fetch from Sandbox API" to begin.
                                    </td>
                                </tr>
                            ) : (
                                results.map((row, idx) => (
                                    <tr key={idx} className={`hover:bg-slate-50 transition-colors ${selectedIds.includes(row.id) ? 'bg-indigo-50/20' : ''}`}>
                                        <td 
                                            className="w-12 text-center cursor-pointer"
                                            onClick={(e) => {
                                                if (row.status !== 'EXACT') {
                                                    e.stopPropagation();
                                                    showError(`Cannot select: Only EXACT MATCH invoices can be pushed to GSTR-3B (Current status: ${row.status.replace('_', ' ')}).`);
                                                }
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.includes(row.id)}
                                                disabled={row.status !== 'EXACT'}
                                                onChange={() => toggleSelectRow(row.id)}
                                                className={`rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4 ${
                                                    row.status === 'EXACT' ? 'cursor-pointer' : 'cursor-not-allowed opacity-30 bg-slate-100'
                                                }`}
                                                title={row.status === 'EXACT' ? 'Select for GSTR-3B Push' : `Cannot select: Status is ${row.status.replace('_', ' ')}`}
                                            />
                                        </td>
                                        <td>
                                            <div className="flex flex-col gap-1 items-start">
                                                <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full 
                                                    ${row.status === 'EXACT' ? 'bg-emerald-100 text-emerald-800' :
                                                      row.status === 'PARTIAL' ? 'bg-indigo-100 text-indigo-800' :
                                                      row.status === 'MISMATCH' ? 'bg-amber-100 text-amber-800' :
                                                      row.status === 'MISSING_BOOKS' ? 'bg-rose-100 text-rose-800' :
                                                      'bg-slate-100 text-slate-800'}`}>
                                                    {row.status.replace('_', ' ')}
                                                </span>
                                                {row.pushed_to_gstr3b && (
                                                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-bold rounded bg-teal-50 text-teal-700 border border-teal-200">
                                                        ✓ Pushed to GSTR-3B
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="font-medium text-slate-800">{row.supplier_gstin}</td>
                                        <td>{row.invoice_no}</td>
                                        <td>{row.invoice_date}</td>
                                        <td className="font-semibold">₹{Number(row.invoice_value).toFixed(2)}</td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
                                                    <div 
                                                        className={`h-full ${row.matching_score >= 100 ? 'bg-emerald-500' : row.matching_score >= 50 ? 'bg-indigo-500' : 'bg-rose-500'}`} 
                                                        style={{ width: `${row.matching_score}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-xs text-slate-500 font-medium">{row.matching_score}%</span>
                                            </div>
                                        </td>
                                        <td>
                                            <button 
                                                onClick={() => setSelectedRow(row)}
                                                className="text-indigo-600 hover:text-indigo-800 text-sm font-semibold transition-colors"
                                            >
                                                Review
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Review Modal */}
            {selectedRow && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="flex justify-between items-center p-4 border-b border-slate-100 bg-slate-50/50">
                            <div>
                                <h3 className="text-lg font-bold text-slate-900">Reconciliation Review</h3>
                                <p className="text-sm text-slate-500">Match Analysis for Invoice {selectedRow.invoice_no}</p>
                            </div>
                            <button onClick={() => setSelectedRow(null)} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto space-y-6">
                            {/* Blocked ITC Error Banner */}
                            {(selectedRow.itc_availability === 'NO' || selectedRow.itc_availment === 'NO' || String(selectedRow.raw_data?.itcavl || '').toUpperCase() === 'N') && (
                                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center shrink-0">
                                        <svg className="w-5 h-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>
                                    </div>
                                    <div>
                                        <div className="text-xs font-bold text-rose-900 uppercase tracking-wide">ITC Availment is Blocked</div>
                                        <div className="text-xs text-rose-700">Government GSTR-2B has marked this invoice as ineligible for ITC. Input Tax Credit cannot be claimed.</div>
                                    </div>
                                </div>
                            )}

                            {/* Mismatch Alert Banner */}
                            {selectedRow.mismatches && selectedRow.mismatches.length > 0 && selectedRow.status !== 'MISSING_BOOKS' && (
                                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg">
                                    <div className="text-xs font-bold text-rose-800 uppercase tracking-wide mb-1">Mismatches Detected:</div>
                                    <div className="flex flex-wrap gap-2">
                                        {selectedRow.mismatches.map((m: string, i: number) => (
                                            <span key={i} className="px-2 py-0.5 bg-rose-100 text-rose-700 rounded text-xs font-semibold">
                                                ⚠️ {m}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-8">
                                {/* GSTR-2B Data */}
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-indigo-100">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                                        <h4 className="font-bold text-indigo-900">Government Data (GSTR-2B)</h4>
                                    </div>
                                    <div className="bg-indigo-50/30 p-4 rounded-lg border border-indigo-50 space-y-3">
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Supplier Name</div>
                                            <div className="font-medium text-slate-800">{selectedRow.vendor_name || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Supplier GSTIN</div>
                                            <div className="font-medium text-slate-800">{selectedRow.supplier_gstin}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Invoice Number</div>
                                            <div className="font-medium text-slate-800">{selectedRow.invoice_no}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Invoice Date</div>
                                            <div className="font-medium text-slate-800">{selectedRow.invoice_date}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Taxable Value</div>
                                            <div className="font-medium text-slate-800">₹{Number(selectedRow.taxable_value || 0).toFixed(2)}</div>
                                        </div>
                                        <div className="grid grid-cols-3 gap-2">
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">IGST</div>
                                                <div className="font-medium text-slate-800">₹{Number(selectedRow.igst || 0).toFixed(2)}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">CGST</div>
                                                <div className="font-medium text-slate-800">₹{Number(selectedRow.cgst || 0).toFixed(2)}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">SGST</div>
                                                <div className="font-medium text-slate-800">₹{Number(selectedRow.sgst || 0).toFixed(2)}</div>
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                            <div className="font-bold text-indigo-700">₹{Number(selectedRow.invoice_value).toFixed(2)}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">Reverse Charge</div>
                                            <div className="font-medium text-slate-800">{selectedRow.reverse_charge || (selectedRow.raw_data?.rchrg || selectedRow.raw_data?.rev || 'N')}</div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-1">ITC Availability</div>
                                            <div className={`font-semibold ${selectedRow.itc_availability === 'YES' || selectedRow.itc_availment === 'YES' ? 'text-emerald-700' : 'text-rose-700'}`}>{selectedRow.itc_availability || selectedRow.itc_availment || 'YES'}</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Books Data */}
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-teal-100">
                                        <div className="w-2 h-2 rounded-full bg-teal-500"></div>
                                        <h4 className="font-bold text-teal-900">Your Books (Purchase Voucher)</h4>
                                    </div>
                                    {selectedRow.books_data ? (
                                        <div className="bg-teal-50/30 p-4 rounded-lg border border-teal-50 space-y-3">
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Supplier Name</div>
                                                <div className={`font-medium ${selectedRow.books_data.vendor_name !== selectedRow.vendor_name ? 'text-indigo-600 bg-indigo-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.vendor_name || 'N/A'}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Supplier GSTIN</div>
                                                <div className="font-medium text-slate-800">{selectedRow.books_data.supplier_gstin || selectedRow.supplier_gstin}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Number</div>
                                                <div className={`font-medium ${selectedRow.books_data.invoice_no?.toLowerCase() !== selectedRow.invoice_no?.toLowerCase() ? 'text-indigo-600 bg-indigo-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.invoice_no}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Date</div>
                                                <div className={`font-medium ${selectedRow.books_data.invoice_date !== selectedRow.invoice_date ? 'text-indigo-600 bg-indigo-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.invoice_date}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Taxable Value</div>
                                                <div className={`font-medium ${Math.abs(Number(selectedRow.books_data.taxable_value || 0) - Number(selectedRow.taxable_value || 0)) > 1 ? 'text-rose-600 bg-rose-50 px-1 rounded' : 'text-slate-800'}`}>₹{Number(selectedRow.books_data.taxable_value || 0).toFixed(2)}</div>
                                            </div>
                                            <div className="grid grid-cols-3 gap-2">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">IGST</div>
                                                    <div className={`font-medium ${Math.abs(Number(selectedRow.books_data.igst || 0) - Number(selectedRow.igst || 0)) > 1 ? 'text-rose-600 bg-rose-50 px-1 rounded' : 'text-slate-800'}`}>₹{Number(selectedRow.books_data.igst || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">CGST</div>
                                                    <div className={`font-medium ${Math.abs(Number(selectedRow.books_data.cgst || 0) - Number(selectedRow.cgst || 0)) > 1 ? 'text-rose-600 bg-rose-50 px-1 rounded' : 'text-slate-800'}`}>₹{Number(selectedRow.books_data.cgst || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">SGST</div>
                                                    <div className={`font-medium ${Math.abs(Number(selectedRow.books_data.sgst || 0) - Number(selectedRow.sgst || 0)) > 1 ? 'text-rose-600 bg-rose-50 px-1 rounded' : 'text-slate-800'}`}>₹{Number(selectedRow.books_data.sgst || 0).toFixed(2)}</div>
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                                <div className={`font-bold ${Math.abs(Number(selectedRow.books_data.invoice_value) - Number(selectedRow.invoice_value)) > 1 ? 'text-rose-600 bg-rose-50 px-1 rounded' : 'text-teal-700'}`}>₹{Number(selectedRow.books_data.invoice_value).toFixed(2)}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Reverse Charge</div>
                                                <div className="font-medium text-slate-800">{selectedRow.books_data.reverse_charge || 'N'}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">ITC Availability</div>
                                                <div className="font-medium text-slate-800">{selectedRow.books_data.itc_availability || 'YES'}</div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="h-full flex flex-col items-center justify-center p-8 bg-slate-50 border border-slate-100 border-dashed rounded-lg text-center">
                                            <div className="w-12 h-12 rounded-full bg-rose-100 flex items-center justify-center mb-3">
                                                <svg className="w-6 h-6 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                                            </div>
                                            <h5 className="font-bold text-slate-700 mb-1">Missing in Books</h5>
                                            <p className="text-sm text-slate-500 mb-4">We could not find a matching purchase voucher for this invoice in your system.</p>
                                            <button 
                                                onClick={() => {
                                                    if (onNavigate) {
                                                        onNavigate('Vouchers', {
                                                             action: 'create',
                                                             type: 'Purchase',
                                                             prefilledData: {
                                                                 sellerName: selectedRow.vendor_name,
                                                                 gstin: selectedRow.supplier_gstin,
                                                                 invoiceNumber: selectedRow.invoice_no,
                                                                 invoiceDate: selectedRow.invoice_date,
                                                                 totalAmount: selectedRow.invoice_value,
                                                                 lineItems: [{
                                                                     itemDescription: 'GSTR-2B Reconciled Purchase',
                                                                     quantity: 1,
                                                                     rate: Number(selectedRow.taxable_value || selectedRow.invoice_value || 0),
                                                                     taxableValue: Number(selectedRow.taxable_value || selectedRow.invoice_value || 0),
                                                                     invoiceValue: Number(selectedRow.invoice_value || 0),
                                                                     gstRate: 0,
                                                                     igst: Number(selectedRow.igst || 0),
                                                                     cgst: Number(selectedRow.cgst || 0),
                                                                     sgst: Number(selectedRow.sgst || 0),
                                                                     cess: Number(selectedRow.cess || 0)
                                                                 }]
                                                             },
                                                             returnTo: 'GST',
                                                             returnTab: 'GSTR2B_RECO'
                                                         });
                                                     }
                                                 }}
                                                 className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-semibold transition-colors">
                                                 Create Purchase Voucher
                                             </button>
                                         </div>
                                     )}
                                 </div>
                             </div>

                             {/* 12-Field Validation Audit Matrix */}
                             {selectedRow.matching_details?.fields && selectedRow.matching_details.fields.length > 0 && (
                                 <div className="border-t border-slate-100 pt-4">
                                     <h4 className="text-sm font-bold text-slate-800 mb-3">12-Field Validation Audit</h4>
                                     <div className="overflow-x-auto rounded border border-slate-200">
                                         <table className="w-full text-xs text-left">
                                             <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                                                 <tr>
                                                     <th className="p-2">Validation Field</th>
                                                     <th className="p-2">Government GSTR-2B</th>
                                                     <th className="p-2">Purchase Books</th>
                                                     <th className="p-2">Difference</th>
                                                     <th className="p-2">Result</th>
                                                 </tr>
                                             </thead>
                                             <tbody className="divide-y divide-slate-100">
                                                 {selectedRow.matching_details.fields.map((f: any, idx: number) => (
                                                     <tr key={idx} className={f.status === 'MISMATCH' || f.status === 'BLOCKED' ? 'bg-rose-50/50' : ''}>
                                                         <td className="p-2 font-medium text-slate-800">{f.field}</td>
                                                         <td className="p-2 text-indigo-700">{typeof f.gstr2b === 'number' ? `₹${f.gstr2b.toFixed(2)}` : String(f.gstr2b ?? 'N/A')}</td>
                                                         <td className="p-2 text-teal-700">{typeof f.books === 'number' ? `₹${f.books.toFixed(2)}` : String(f.books ?? 'N/A')}</td>
                                                         <td className="p-2 text-slate-600">{f.difference !== undefined ? `₹${Number(f.difference).toFixed(2)}` : '-'}</td>
                                                         <td className="p-2">
                                                             <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                                                 f.status === 'MATCH' ? 'bg-emerald-100 text-emerald-800' :
                                                                 f.status === 'BLOCKED' ? 'bg-rose-100 text-rose-800' :
                                                                 'bg-rose-100 text-rose-800'}`}>
                                                                 {f.status}
                                                             </span>
                                                         </td>
                                                     </tr>
                                                 ))}
                                             </tbody>
                                         </table>
                                     </div>
                                 </div>
                             )}
                         </div>
                         <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center gap-3">
                            <div>
                                {selectedRow?.books_data?.purchase_voucher_id && (
                                    <button
                                        onClick={() => {
                                            if (setViewVoucherData && onNavigate) {
                                                setViewVoucherData({
                                                    id: selectedRow.books_data.purchase_voucher_id,
                                                    voucherNo: selectedRow.books_data.invoice_no,
                                                    type: 'Purchase',
                                                    source: 'purchase_gstr2b_reco_drilldown',
                                                    returnTo: 'GST',
                                                    returnTab: 'GSTR2B_RECO',
                                                    // Pass GSTR-2B expected values so the form can highlight mismatches
                                                    gstr2b_invoice_date: selectedRow.invoice_date,
                                                    gstr2b_invoice_no: selectedRow.invoice_no,
                                                    gstr2b_invoice_value: selectedRow.invoice_value,
                                                    gstr2b_gstin: selectedRow.supplier_gstin,
                                                    gstr2b_vendor_name: selectedRow.vendor_name,
                                                });
                                                setSelectedRow(null);
                                                onNavigate('Vouchers');
                                            }
                                        }}
                                        className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded shadow text-sm font-semibold transition-all flex items-center gap-2"
                                    >
                                        ✏️ Open Purchase Voucher to Fix
                                    </button>
                                )}
                            </div>
                            <div className="flex gap-3">
                                <button onClick={() => setSelectedRow(null)} className="px-4 py-2 text-slate-600 hover:text-slate-900 font-semibold text-sm transition-colors">
                                    Close
                                </button>
                                <button 
                                    onClick={() => {
                                        if (selectedRow.itc_availability === 'NO' || selectedRow.itc_availment === 'NO' || String(selectedRow.raw_data?.itcavl || '').toUpperCase() === 'N') {
                                            alert("⚠️ ACTION BLOCKED\n\nYour ITC Availment is blocked!\n\nGovernment GSTR-2B has marked this invoice as ineligible for Input Tax Credit. You cannot legally claim ITC for this invoice.");
                                            return;
                                        }
                                        if (selectedRow.books_data) {
                                            const invoiceNoMatch = selectedRow.invoice_no?.toLowerCase() === selectedRow.books_data.invoice_no?.toLowerCase();
                                            if (!invoiceNoMatch) {
                                                alert("⚠️ ACTION BLOCKED\n\nCompulsory fields (Invoice Number) do not match!\n\nYou cannot legally accept this match for ITC. Please click 'Open Purchase Voucher to Fix' and correct your books first.");
                                                return;
                                            }
                                        } else if (selectedRow.status === 'MISSING_BOOKS' || selectedRow.status === 'MISSING_2B') {
                                            alert("⚠️ ACTION BLOCKED\n\nThis invoice is missing from one side. You must create a matching voucher before you can accept a match.");
                                            return;
                                        }
                                        showSuccess('Match Accepted and ITC computed');
                                        setSelectedRow(null);
                                    }}
                                    className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded shadow text-sm font-semibold transition-all">
                                    Accept Match
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Push Confirmation Modal */}
            {showPushConfirmModal && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
                        <div className="flex justify-between items-center p-4 border-b border-slate-100 bg-slate-50/50">
                            <div className="flex items-center gap-2">
                                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
                                <h3 className="text-base font-bold text-slate-900">Push to GSTR-3B?</h3>
                            </div>
                            <button onClick={() => setShowPushConfirmModal(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <p className="text-sm text-slate-600">
                                <span className="font-bold text-slate-900">{selectedCount}</span> exact-match invoices are selected for period <span className="font-semibold text-indigo-700">{selectedMonth} {selectedYear}</span>.
                            </p>
                            
                            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                                <div className="flex justify-between text-slate-600">
                                    <span>IGST:</span>
                                    <span className="font-semibold text-slate-900">₹{totalEligibleIGST.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-slate-600">
                                    <span>CGST:</span>
                                    <span className="font-semibold text-slate-900">₹{totalEligibleCGST.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-slate-600">
                                    <span>SGST:</span>
                                    <span className="font-semibold text-slate-900">₹{totalEligibleSGST.toFixed(2)}</span>
                                </div>
                                {totalEligibleCESS > 0 && (
                                    <div className="flex justify-between text-slate-600">
                                        <span>CESS:</span>
                                        <span className="font-semibold text-slate-900">₹{totalEligibleCESS.toFixed(2)}</span>
                                    </div>
                                )}
                                <div className="border-t border-slate-200 pt-2 flex justify-between font-bold text-sm text-emerald-800">
                                    <span>Total Eligible ITC:</span>
                                    <span>₹{totalEligibleITC.toFixed(2)}</span>
                                </div>
                            </div>

                            <p className="text-xs text-slate-500 italic">
                                * Only EXACT MATCH invoices with ITC Availability = YES will be credited to GSTR-3B Input Tax Credit.
                            </p>
                        </div>
                        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
                            <button
                                onClick={() => setShowPushConfirmModal(false)}
                                disabled={isPushing}
                                className="px-4 py-2 text-slate-600 hover:text-slate-900 font-semibold text-sm transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handlePushToGSTR3B}
                                disabled={isPushing}
                                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded shadow text-sm font-semibold transition-all flex items-center gap-2"
                            >
                                {isPushing ? 'Pushing...' : 'Push to GSTR-3B'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
