import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';
import { apiService } from '../../services/api';
import { showSuccess, showError } from '../../utils/toast';
import { getXLSX } from '../../utils/xlsx';

export default function GSTR2Reconciliation({ onNavigate, setViewVoucherData, refreshKey, navParams }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void, refreshKey?: number, navParams?: any }) {
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

    const formatPeriod = (fp?: string, defaultMonth?: string, defaultYear?: string) => {
        if (!fp) return defaultMonth && defaultYear ? `${defaultMonth} ${defaultYear}` : (selectedMonth ? `${selectedMonth} ${selectedYear}` : 'N/A');
        const s = String(fp).trim();
        if (/^\d{6}$/.test(s)) {
            const monthNum = parseInt(s.substring(0, 2), 10);
            const yearNum = s.substring(2);
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            if (monthNum >= 1 && monthNum <= 12) {
                return `${monthNames[monthNum - 1]} ${yearNum}`;
            }
        }
        return s;
    };

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
        // Only clear if month/year changed by user and not restoring session
        if (sessionStorage.getItem('reco_bulk_review_open') !== 'true') {
            setSelectedExactIds([]);
            setSelectedPartialIds([]);
        }
        fetchResults();
    }, [selectedMonth, selectedYear]);

    type StatusFilter = 'ALL' | 'EXACT' | 'PUSHED_3B' | 'PARTIAL' | 'MISSING_BOOKS' | 'MISSING_2B';
    const [activeStatusFilter, setActiveStatusFilter] = useState<StatusFilter>('ALL');

    const handleFilterToggle = (filter: StatusFilter) => {
        setActiveStatusFilter(prev => prev === filter ? 'ALL' : filter);
    };

    const filteredResults = results.filter(row => {
        if (activeStatusFilter === 'EXACT') return row.status === 'EXACT' && !row.pushed_to_gstr3b;
        if (activeStatusFilter === 'PUSHED_3B') return Boolean(row.pushed_to_gstr3b);
        if (activeStatusFilter === 'PARTIAL') return row.status === 'PARTIAL' || row.status === 'MISMATCH';
        if (activeStatusFilter === 'MISSING_BOOKS') return row.status === 'MISSING_BOOKS';
        if (activeStatusFilter === 'MISSING_2B') return row.status === 'MISSING_2B';
        return true;
    });

    // Selection states with sessionStorage persistence
    const [selectedExactIds, setSelectedExactIds] = useState<number[]>([]);
    const [selectedPartialIds, setSelectedPartialIds] = useState<number[]>(() => {
        try {
            const stored = sessionStorage.getItem('reco_selected_partial_ids');
            if (stored) {
                const parsed = JSON.parse(stored);
                if (Array.isArray(parsed) && parsed.length > 0) return parsed;
            }
        } catch { }
        return [];
    });
    const [showBulkErrorModal, setShowBulkErrorModal] = useState<boolean>(() => {
        try {
            return sessionStorage.getItem('reco_bulk_review_open') === 'true';
        } catch { }
        return false;
    });
    const [selectedErrorKeys, setSelectedErrorKeys] = useState<string[]>([]);

    // Save selection & modal state to sessionStorage
    useEffect(() => {
        try {
            if (selectedPartialIds.length > 0) {
                sessionStorage.setItem('reco_selected_partial_ids', JSON.stringify(selectedPartialIds));
            }
        } catch { }
    }, [selectedPartialIds]);

    useEffect(() => {
        try {
            if (showBulkErrorModal) {
                sessionStorage.setItem('reco_bulk_review_open', 'true');
            } else {
                sessionStorage.removeItem('reco_bulk_review_open');
            }
        } catch { }
    }, [showBulkErrorModal]);

    // If navParams has returnBulkReview, open modal
    useEffect(() => {
        if (navParams?.returnBulkReview || sessionStorage.getItem('reco_bulk_review_open') === 'true') {
            setShowBulkErrorModal(true);
        }
    }, [navParams]);

    // Exact Match Selection calculations (only unpushed exact rows are eligible for push)
    const exactRows = results.filter(r => r.status === 'EXACT');
    const unpushedExactRows = exactRows.filter(r => !r.pushed_to_gstr3b);
    const visibleExactRows = filteredResults.filter(r => r.status === 'EXACT');
    const visibleUnpushedExactRows = visibleExactRows.filter(r => !r.pushed_to_gstr3b);
    const selectedExactRows = unpushedExactRows.filter(r => selectedExactIds.includes(r.id));
    const selectedExactCount = selectedExactRows.length;
    const isAllExactSelected = visibleUnpushedExactRows.length > 0 && visibleUnpushedExactRows.every(r => selectedExactIds.includes(r.id));

    // Partial / Mismatch Selection calculations
    const partialRows = results.filter(r => r.status === 'PARTIAL' || r.status === 'MISMATCH');
    const visiblePartialRows = filteredResults.filter(r => r.status === 'PARTIAL' || r.status === 'MISMATCH');
    const selectedPartialRows = partialRows.filter(r => selectedPartialIds.includes(r.id));
    const selectedPartialCount = selectedPartialRows.length;
    const isAllPartialSelected = visiblePartialRows.length > 0 && visiblePartialRows.every(r => selectedPartialIds.includes(r.id));

    const toggleSelectAllExact = () => {
        if (visibleUnpushedExactRows.length === 0) return;
        if (isAllExactSelected) {
            const visibleIds = visibleUnpushedExactRows.map(r => r.id);
            setSelectedExactIds(prev => prev.filter(id => !visibleIds.includes(id)));
        } else {
            const visibleIds = visibleUnpushedExactRows.map(r => r.id);
            setSelectedExactIds(prev => Array.from(new Set([...prev, ...visibleIds])));
        }
    };

    const toggleSelectAllPartial = () => {
        if (visiblePartialRows.length === 0) return;
        if (isAllPartialSelected) {
            const visibleIds = visiblePartialRows.map(r => r.id);
            setSelectedPartialIds(prev => prev.filter(id => !visibleIds.includes(id)));
        } else {
            const visibleIds = visiblePartialRows.map(r => r.id);
            setSelectedPartialIds(prev => Array.from(new Set([...prev, ...visibleIds])));
        }
    };

    const toggleSelectRow = (row: any) => {
        if (row.pushed_to_gstr3b) return;
        if (row.status === 'EXACT') {
            setSelectedExactIds(prev =>
                prev.includes(row.id) ? prev.filter(item => item !== row.id) : [...prev, row.id]
            );
        } else if (row.status === 'PARTIAL' || row.status === 'MISMATCH') {
            setSelectedPartialIds(prev =>
                prev.includes(row.id) ? prev.filter(item => item !== row.id) : [...prev, row.id]
            );
        }
    };

    // Mismatch Categories Definition for Bulk Review Analysis
    const MISMATCH_CATEGORIES = [
        { key: 'INVOICE VALUE MISMATCH', label: 'Invoice Value Mismatch', shortLabel: 'Invoice Value' },
        { key: 'TAXABLE VALUE MISMATCH', label: 'Taxable Value Mismatch', shortLabel: 'Taxable Value' },
        { key: 'IGST MISMATCH', label: 'IGST Mismatch', shortLabel: 'IGST' },
        { key: 'CGST MISMATCH', label: 'CGST Mismatch', shortLabel: 'CGST' },
        { key: 'SGST MISMATCH', label: 'SGST Mismatch', shortLabel: 'SGST' },
        { key: 'INVOICE DATE MISMATCH', label: 'Invoice Date Mismatch', shortLabel: 'Invoice Date' },
        { key: 'REVERSE CHARGE MISMATCH', label: 'Reverse Charge Mismatch', shortLabel: 'Reverse Charge' },
        { key: 'PERIOD MISMATCH', label: 'Period Mismatch', shortLabel: 'Period' },
        { key: 'GSTIN MISMATCH', label: 'GSTIN Mismatch', shortLabel: 'GSTIN' },
        { key: 'ITC AVAILMENT BLOCKED', label: 'ITC Blocked / Ineligible', shortLabel: 'ITC Blocked' },
    ];

    const invoiceHasMismatch = (row: any, key: string): boolean => {
        const mismatches = (row.mismatches || []).map((m: string) => m.toUpperCase());
        if (mismatches.includes(key.toUpperCase())) return true;
        const fields = row.matching_details?.fields || [];
        if (key === 'INVOICE VALUE MISMATCH') return fields.some((f: any) => f.field === 'Invoice Value' && f.status === 'MISMATCH');
        if (key === 'TAXABLE VALUE MISMATCH') return fields.some((f: any) => f.field === 'Taxable Value' && f.status === 'MISMATCH');
        if (key === 'IGST MISMATCH') return fields.some((f: any) => f.field === 'IGST' && f.status === 'MISMATCH');
        if (key === 'CGST MISMATCH') return fields.some((f: any) => f.field === 'CGST' && f.status === 'MISMATCH');
        if (key === 'SGST MISMATCH') return fields.some((f: any) => f.field === 'SGST' && f.status === 'MISMATCH');
        if (key === 'INVOICE DATE MISMATCH') return fields.some((f: any) => f.field === 'Invoice Date' && f.status === 'MISMATCH');
        if (key === 'REVERSE CHARGE MISMATCH') return fields.some((f: any) => f.field === 'Reverse Charge' && f.status === 'MISMATCH');
        if (key === 'PERIOD MISMATCH') return fields.some((f: any) => f.field === 'GSTR-2B Period' && f.status === 'MISMATCH');
        if (key === 'GSTIN MISMATCH') return fields.some((f: any) => f.field === 'Supplier GSTIN' && f.status === 'MISMATCH');
        if (key === 'ITC AVAILMENT BLOCKED') return row.itc_availability === 'NO' || row.itc_availment === 'NO' || fields.some((f: any) => f.field === 'ITC Availability' && f.status === 'BLOCKED');
        return false;
    };

    const getInvoiceValidationFields = (row: any) => {
        if (row.matching_details?.fields && Array.isArray(row.matching_details.fields) && row.matching_details.fields.length > 0) {
            return row.matching_details.fields.filter((f: any) => f.field !== 'Total Value');
        }
        const b = row.books_data || {};
        const mismatches = (row.mismatches || []).map((m: string) => m.toUpperCase());
        const gstr2bVal = Number(row.invoice_value || 0);
        const booksVal = Number(b.invoice_value || 0);
        const gstr2bTx = Number(row.taxable_value || 0);
        const booksTx = Number(b.taxable_value || 0);
        const gstr2bIgst = Number(row.igst || 0);
        const booksIgst = Number(b.igst || 0);
        const gstr2bCgst = Number(row.cgst || 0);
        const booksCgst = Number(b.cgst || 0);
        const gstr2bSgst = Number(row.sgst || 0);
        const booksSgst = Number(b.sgst || 0);

        return [
            { field: 'Supplier GSTIN', gstr2b: row.supplier_gstin || '-', books: b.supplier_gstin || '-', status: mismatches.some(m => m.includes('GSTIN')) ? 'MISMATCH' : 'MATCH' },
            { field: 'Invoice Number', gstr2b: row.invoice_no || '-', books: b.invoice_no || '-', status: mismatches.some(m => m.includes('NUMBER')) ? 'MISMATCH' : 'MATCH' },
            { field: 'Invoice Date', gstr2b: row.invoice_date || '-', books: b.invoice_date || '-', status: mismatches.some(m => m.includes('DATE')) ? 'MISMATCH' : 'MATCH' },
            { field: 'Invoice Value', gstr2b: gstr2bVal, books: booksVal, difference: gstr2bVal - booksVal, status: mismatches.some(m => m.includes('INVOICE VALUE')) ? 'MISMATCH' : 'MATCH' },
            { field: 'Taxable Value', gstr2b: gstr2bTx, books: booksTx, difference: gstr2bTx - booksTx, status: mismatches.some(m => m.includes('TAXABLE VALUE')) ? 'MISMATCH' : 'MATCH' },
            { field: 'IGST', gstr2b: gstr2bIgst, books: booksIgst, difference: gstr2bIgst - booksIgst, status: mismatches.some(m => m.includes('IGST')) ? 'MISMATCH' : 'MATCH' },
            { field: 'CGST', gstr2b: gstr2bCgst, books: booksCgst, difference: gstr2bCgst - booksCgst, status: mismatches.some(m => m.includes('CGST')) ? 'MISMATCH' : 'MATCH' },
            { field: 'SGST', gstr2b: gstr2bSgst, books: booksSgst, difference: gstr2bSgst - booksSgst, status: mismatches.some(m => m.includes('SGST')) ? 'MISMATCH' : 'MATCH' },
            { field: 'GSTR-2B Period', gstr2b: row.gstr_period || row.raw_data?.fp || '-', books: b.gstr_period || `${selectedMonth} ${selectedYear}`, status: mismatches.some(m => m.includes('PERIOD')) ? 'MISMATCH' : 'MATCH' },
            { field: 'Reverse Charge', gstr2b: row.reverse_charge || 'N', books: b.reverse_charge || 'N', status: mismatches.some(m => m.includes('REVERSE CHARGE')) ? 'MISMATCH' : 'MATCH' },
            { field: 'ITC Availability', gstr2b: (row.itc_availability === 'NO' || row.itc_availment === 'NO') ? 'NO (Blocked)' : 'YES', books: (b.itc_availability === 'NO') ? 'NO (Blocked)' : 'YES', status: (row.itc_availability === 'NO' || row.itc_availment === 'NO' || mismatches.some(m => m.includes('ITC'))) ? 'BLOCKED' : 'MATCH' },
        ];
    };

    const categoryCounts = MISMATCH_CATEGORIES.map(cat => ({
        ...cat,
        count: selectedPartialRows.filter(r => invoiceHasMismatch(r, cat.key)).length
    }));

    const toggleErrorCategory = (key: string) => {
        setSelectedErrorKeys(prev =>
            prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
        );
    };

    const selectAllErrorCategories = () => {
        const activeKeys = categoryCounts.filter(c => c.count > 0).map(c => c.key);
        setSelectedErrorKeys(activeKeys);
    };

    const clearAllErrorCategories = () => {
        setSelectedErrorKeys([]);
    };

    const modalFilteredInvoices = selectedErrorKeys.length > 0
        ? selectedPartialRows.filter(r => selectedErrorKeys.some(key => invoiceHasMismatch(r, key)))
        : selectedPartialRows;

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
            setSelectedExactIds([]);
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
                try { await fetchResults(); } catch (_) { }
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
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-6 mt-4">
                    {/* Exact Match (Pending) */}
                    <div
                        onClick={() => handleFilterToggle('EXACT')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilterToggle('EXACT')}
                        title="Click to show only Exact Match invoices pending push (Click again to show all)"
                        className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer select-none relative overflow-hidden group ${activeStatusFilter === 'EXACT'
                            ? 'bg-emerald-100/90 border-emerald-500 ring-2 ring-emerald-500 shadow-md transform -translate-y-0.5'
                            : 'bg-emerald-50/70 border-emerald-200/70 hover:border-emerald-400 hover:bg-emerald-50 hover:shadow-sm hover:-translate-y-0.5'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-emerald-800 font-semibold flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                                Exact Match
                            </span>
                            {activeStatusFilter === 'EXACT' ? (
                                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 bg-emerald-700 text-white rounded-full shadow-sm">
                                    Active Filter ✓
                                </span>
                            ) : (
                                <span className="text-[11px] text-emerald-700/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Click to filter
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                            <div className="text-2xl font-black text-emerald-950">
                                {summary.unpushed_exact ?? Math.max(0, (summary.exact_match || 0) - (summary.pushed_exact || 0))}
                            </div>
                            <span className="text-xs text-emerald-700/80 font-medium">Pending Push</span>
                        </div>
                    </div>

                    {/* Pushed to GSTR-3B */}
                    <div
                        onClick={() => handleFilterToggle('PUSHED_3B')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilterToggle('PUSHED_3B')}
                        title="Click to show only invoices pushed to GSTR-3B (Click again to show all)"
                        className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer select-none relative overflow-hidden group ${activeStatusFilter === 'PUSHED_3B'
                            ? 'bg-teal-100/90 border-teal-500 ring-2 ring-teal-500 shadow-md transform -translate-y-0.5'
                            : 'bg-teal-50/70 border-teal-200/70 hover:border-teal-400 hover:bg-teal-50 hover:shadow-sm hover:-translate-y-0.5'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-teal-900 font-semibold flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-teal-500"></span>
                                Pushed to 3B
                            </span>
                            {activeStatusFilter === 'PUSHED_3B' ? (
                                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 bg-teal-800 text-white rounded-full shadow-sm">
                                    Active Filter ✓
                                </span>
                            ) : (
                                <span className="text-[11px] text-teal-700/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Click to filter
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                            <div className="text-2xl font-black text-teal-950">
                                {summary.pushed_exact || 0}
                            </div>
                            <span className="text-xs text-teal-800/80 font-medium">In GSTR-3B</span>
                        </div>
                    </div>

                    {/* Partial / Mismatch */}
                    <div
                        onClick={() => handleFilterToggle('PARTIAL')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilterToggle('PARTIAL')}
                        title="Click to show only Partial / Mismatch invoices (Click again to show all)"
                        className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer select-none relative overflow-hidden group ${activeStatusFilter === 'PARTIAL'
                            ? 'bg-indigo-100/90 border-indigo-500 ring-2 ring-indigo-500 shadow-md transform -translate-y-0.5'
                            : 'bg-indigo-50/70 border-indigo-200/70 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-sm hover:-translate-y-0.5'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-indigo-800 font-semibold flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                                Partial / Mismatch
                            </span>
                            {activeStatusFilter === 'PARTIAL' ? (
                                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 bg-indigo-700 text-white rounded-full shadow-sm">
                                    Active Filter ✓
                                </span>
                            ) : (
                                <span className="text-[11px] text-indigo-700/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Click to filter
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                            <div className="text-2xl font-black text-indigo-950">{(summary.partial_match || 0) + (summary.mismatch || 0)}</div>
                            <span className="text-xs text-indigo-700/80 font-medium">Invoices</span>
                        </div>
                    </div>

                    {/* Missing in Books */}
                    <div
                        onClick={() => handleFilterToggle('MISSING_BOOKS')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilterToggle('MISSING_BOOKS')}
                        title="Click to show only Missing in Books invoices (Click again to show all)"
                        className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer select-none relative overflow-hidden group ${activeStatusFilter === 'MISSING_BOOKS'
                            ? 'bg-rose-100/90 border-rose-500 ring-2 ring-rose-500 shadow-md transform -translate-y-0.5'
                            : 'bg-rose-50/70 border-rose-200/70 hover:border-rose-400 hover:bg-rose-50 hover:shadow-sm hover:-translate-y-0.5'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-rose-800 font-semibold flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                                Missing in Books
                            </span>
                            {activeStatusFilter === 'MISSING_BOOKS' ? (
                                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 bg-rose-700 text-white rounded-full shadow-sm">
                                    Active Filter ✓
                                </span>
                            ) : (
                                <span className="text-[11px] text-rose-700/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Click to filter
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                            <div className="text-2xl font-black text-rose-950">{summary.missing_in_books}</div>
                            <span className="text-xs text-rose-700/80 font-medium">Invoices</span>
                        </div>
                    </div>

                    {/* Missing in 2B */}
                    <div
                        onClick={() => handleFilterToggle('MISSING_2B')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && handleFilterToggle('MISSING_2B')}
                        title="Click to show only Missing in 2B invoices (Click again to show all)"
                        className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer select-none relative overflow-hidden group ${activeStatusFilter === 'MISSING_2B'
                            ? 'bg-slate-200 border-slate-600 ring-2 ring-slate-600 shadow-md transform -translate-y-0.5'
                            : 'bg-slate-50/80 border-slate-200/80 hover:border-slate-400 hover:bg-slate-100/80 hover:shadow-sm hover:-translate-y-0.5'
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-slate-800 font-semibold flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                                Missing in 2B
                            </span>
                            {activeStatusFilter === 'MISSING_2B' ? (
                                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 bg-slate-800 text-white rounded-full shadow-sm">
                                    Active Filter ✓
                                </span>
                            ) : (
                                <span className="text-[11px] text-slate-700/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Click to filter
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                            <div className="text-2xl font-black text-slate-950">{summary.missing_in_2b}</div>
                            <span className="text-xs text-slate-700/80 font-medium">Invoices</span>
                        </div>
                    </div>
                </div>

                <div className="flex flex-wrap justify-between items-center mb-3 gap-3">
                    <div className="flex items-center flex-wrap gap-2.5">
                        <h3 className="text-sm font-semibold text-gray-700">
                            Currently viewing GSTR-2B data for: <span className="text-indigo-900 font-bold">{selectedMonth} {selectedYear}</span>
                        </h3>
                        {activeStatusFilter !== 'ALL' && (
                            <div className="flex items-center gap-2">
                                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                                    <span>Filtered:</span>
                                    <strong className="font-bold">
                                        {activeStatusFilter === 'EXACT' && 'Exact Match (Pending Push)'}
                                        {activeStatusFilter === 'PUSHED_3B' && 'Pushed to GSTR-3B'}
                                        {activeStatusFilter === 'PARTIAL' && 'Partial / Mismatch'}
                                        {activeStatusFilter === 'MISSING_BOOKS' && 'Missing in Books'}
                                        {activeStatusFilter === 'MISSING_2B' && 'Missing in 2B'}
                                    </strong>
                                    <span className="text-xs font-normal opacity-80">({filteredResults.length})</span>
                                    <button
                                        onClick={() => setActiveStatusFilter('ALL')}
                                        className="ml-1 text-indigo-600 hover:text-indigo-900 font-bold text-sm leading-none focus:outline-none cursor-pointer"
                                        title="Clear filter"
                                    >
                                        ✕
                                    </button>
                                </span>
                                <button
                                    onClick={() => setActiveStatusFilter('ALL')}
                                    className="text-xs text-slate-500 hover:text-indigo-700 font-medium underline transition-colors cursor-pointer"
                                >
                                    Show All ({results.length})
                                </button>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {activeStatusFilter === 'PARTIAL' ? (
                            <>
                                <span className="text-xs font-semibold px-3 py-1.5 bg-indigo-50 text-indigo-800 rounded border border-indigo-200">
                                    {selectedPartialCount} Partial/Mismatch Selected
                                </span>
                                <button
                                    onClick={() => {
                                        setSelectedErrorKeys([]);
                                        setShowBulkErrorModal(true);
                                    }}
                                    disabled={selectedPartialCount === 0}
                                    className={`px-4 py-1.5 rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 ${selectedPartialCount > 0
                                        ? 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer shadow-indigo-200'
                                        : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                                        }`}
                                >
                                    🔍 BULK REVIEW ERRORS
                                </button>
                            </>
                        ) : activeStatusFilter === 'EXACT' ? (
                            <>
                                <span className="text-xs font-semibold px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded border border-emerald-200">
                                    {selectedExactCount} Exact Matches Selected
                                </span>
                                <button
                                    onClick={() => setShowPushConfirmModal(true)}
                                    disabled={selectedExactCount === 0 || isPushing}
                                    className={`px-4 py-1.5 rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 ${selectedExactCount > 0 && !isPushing
                                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-emerald-200'
                                        : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                                        }`}
                                >
                                    🚀 PUSH TO GSTR-3B
                                </button>
                            </>
                        ) : (
                            <>
                                {selectedPartialCount > 0 && (
                                    <>
                                        <span className="text-xs font-semibold px-3 py-1.5 bg-indigo-50 text-indigo-800 rounded border border-indigo-200">
                                            {selectedPartialCount} Partial Selected
                                        </span>
                                        <button
                                            onClick={() => {
                                                setSelectedErrorKeys([]);
                                                setShowBulkErrorModal(true);
                                            }}
                                            className="px-4 py-1.5 rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer shadow-indigo-200"
                                        >
                                            🔍 BULK REVIEW ERRORS
                                        </button>
                                    </>
                                )}
                                {selectedExactCount > 0 && (
                                    <>
                                        <span className="text-xs font-semibold px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded border border-emerald-200">
                                            {selectedExactCount} Exact Selected
                                        </span>
                                        <button
                                            onClick={() => setShowPushConfirmModal(true)}
                                            disabled={isPushing}
                                            className="px-4 py-1.5 rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-emerald-200"
                                        >
                                            🚀 PUSH TO GSTR-3B
                                        </button>
                                    </>
                                )}
                                {selectedPartialCount === 0 && selectedExactCount === 0 && (
                                    <span className="text-xs font-medium px-3 py-1.5 bg-slate-50 text-slate-500 rounded border border-slate-200">
                                        0 Invoices Selected
                                    </span>
                                )}
                            </>
                        )}
                    </div>
                </div>
                <div className="erp-table-container">
                    <table className="erp-table">
                        <thead>
                            <tr>
                                <th
                                    className="w-12 text-center cursor-pointer"
                                    onClick={(e) => {
                                        if (activeStatusFilter === 'PARTIAL' && visiblePartialRows.length === 0) {
                                            e.stopPropagation();
                                            showError("No Partial/Mismatch invoices available in current view.");
                                        } else if (activeStatusFilter === 'EXACT' && visibleExactRows.length === 0) {
                                            e.stopPropagation();
                                            showError("No EXACT MATCH invoices available in current view.");
                                        }
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={
                                            activeStatusFilter === 'PARTIAL'
                                                ? isAllPartialSelected
                                                : activeStatusFilter === 'EXACT'
                                                    ? isAllExactSelected
                                                    : (visibleExactRows.length > 0 && isAllExactSelected) || (visiblePartialRows.length > 0 && isAllPartialSelected)
                                        }
                                        onChange={() => {
                                            if (activeStatusFilter === 'PARTIAL') {
                                                toggleSelectAllPartial();
                                            } else if (activeStatusFilter === 'EXACT') {
                                                toggleSelectAllExact();
                                            } else {
                                                if (isAllExactSelected || isAllPartialSelected) {
                                                    setSelectedExactIds([]);
                                                    setSelectedPartialIds([]);
                                                } else {
                                                    toggleSelectAllExact();
                                                    toggleSelectAllPartial();
                                                }
                                            }
                                        }}
                                        disabled={
                                            activeStatusFilter === 'PARTIAL'
                                                ? visiblePartialRows.length === 0
                                                : activeStatusFilter === 'EXACT'
                                                    ? visibleExactRows.length === 0
                                                    : visibleExactRows.length === 0 && visiblePartialRows.length === 0
                                        }
                                        className={`rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4 ${(activeStatusFilter === 'PARTIAL' ? visiblePartialRows.length > 0 : activeStatusFilter === 'EXACT' ? visibleExactRows.length > 0 : (visibleExactRows.length > 0 || visiblePartialRows.length > 0))
                                            ? 'cursor-pointer'
                                            : 'cursor-not-allowed opacity-40'
                                            }`}
                                        title={
                                            activeStatusFilter === 'PARTIAL'
                                                ? "Select All Partial/Mismatch"
                                                : activeStatusFilter === 'EXACT'
                                                    ? "Select All Exact Matches"
                                                    : "Select All Visible Selectable Invoices"
                                        }
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
                            ) : filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-12 text-slate-500">
                                        <div className="flex flex-col items-center justify-center gap-2">
                                            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 text-base font-bold">
                                                🔍
                                            </div>
                                            <p className="text-sm font-medium text-slate-600">
                                                No invoices found with status: <strong>{activeStatusFilter.replace('_', ' ')}</strong>
                                            </p>
                                            <button
                                                onClick={() => setActiveStatusFilter('ALL')}
                                                className="mt-1 px-3 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded text-xs font-semibold border border-indigo-200 transition-colors cursor-pointer"
                                            >
                                                View all {results.length} invoices
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredResults.map((row, idx) => {
                                    const isRowExact = row.status === 'EXACT';
                                    const isRowPartial = row.status === 'PARTIAL' || row.status === 'MISMATCH';
                                    const isAlreadyPushed = Boolean(row.pushed_to_gstr3b);
                                    const isSelected = !isAlreadyPushed && (isRowExact ? selectedExactIds.includes(row.id) : isRowPartial ? selectedPartialIds.includes(row.id) : false);

                                    return (
                                        <tr key={idx} className={`hover:bg-slate-50 transition-colors ${isAlreadyPushed ? 'bg-teal-50/20' : isSelected ? (isRowExact ? 'bg-emerald-50/30' : 'bg-indigo-50/30') : ''}`}>
                                            <td
                                                className="w-12 text-center cursor-pointer"
                                                onClick={(e) => {
                                                    if (isAlreadyPushed) {
                                                        e.stopPropagation();
                                                        return;
                                                    }
                                                    if (!isRowExact && !isRowPartial) {
                                                        e.stopPropagation();
                                                        showError(`Cannot select: ${row.status.replace('_', ' ')} invoices are not eligible for bulk actions.`);
                                                    }
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected || isAlreadyPushed}
                                                    disabled={isAlreadyPushed || (!isRowExact && !isRowPartial)}
                                                    onChange={() => !isAlreadyPushed && toggleSelectRow(row)}
                                                    className={`rounded focus:ring-indigo-500 h-4 w-4 ${isAlreadyPushed
                                                        ? 'text-teal-600 bg-teal-50 opacity-70 cursor-not-allowed'
                                                        : isRowExact
                                                            ? 'text-emerald-600 cursor-pointer'
                                                            : isRowPartial
                                                                ? 'text-indigo-600 cursor-pointer'
                                                                : 'cursor-not-allowed opacity-30 bg-slate-100'
                                                        }`}
                                                    title={isAlreadyPushed ? 'Already pushed to GSTR-3B' : isRowExact ? 'Select for GSTR-3B Push' : isRowPartial ? 'Select for Bulk Error Review' : `Cannot select: Status is ${row.status.replace('_', ' ')}`}
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
                                                    {isAlreadyPushed && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal-100 text-teal-800 border border-teal-300">
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
                                                    className="text-indigo-600 hover:text-indigo-800 text-sm font-semibold transition-colors cursor-pointer"
                                                >
                                                    Review
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Review Modal */}
            {selectedRow && (
                <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="flex justify-between items-center p-4 border-b border-slate-100 bg-slate-50/50">
                            <div>
                                <h3 className="text-lg font-bold text-slate-900">Reconciliation Review</h3>
                                <p className="text-sm text-slate-500">Match Analysis for Invoice {selectedRow.invoice_no}</p>
                            </div>
                            <button onClick={() => setSelectedRow(null)} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors cursor-pointer">
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
                            {(() => {
                                const visibleMismatches = (selectedRow.mismatches || []).filter((m: string) => m.toUpperCase() !== 'TOTAL VALUE MISMATCH');
                                if (visibleMismatches.length === 0 || selectedRow.status === 'MISSING_BOOKS') return null;
                                return (
                                    <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg">
                                        <div className="text-xs font-bold text-rose-800 uppercase tracking-wide mb-1">Mismatches Detected:</div>
                                        <div className="flex flex-wrap gap-2">
                                            {visibleMismatches.map((m: string, i: number) => (
                                                <span key={i} className="px-2 py-0.5 bg-rose-100 text-rose-700 rounded text-xs font-semibold">
                                                    ⚠️ {m}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })()}

                            <div className="grid grid-cols-2 gap-8">
                                {/* GSTR-2B Data */}
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-indigo-100">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                                        <h4 className="font-bold text-indigo-900">Government Data (GSTR-2B)</h4>
                                    </div>
                                    {selectedRow.status === 'MISSING_2B' ? (
                                        <div className="h-full flex flex-col items-center justify-center p-8 bg-slate-50 border border-slate-200 border-dashed rounded-xl text-center">
                                            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3 text-slate-500">
                                                <svg className="w-6 h-6 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                                            </div>
                                            <h5 className="font-bold text-slate-700 mb-1">Missing in GSTR-2B</h5>
                                            <p className="text-sm text-slate-500">This invoice exists in your purchase books, but the supplier has not uploaded or filed this invoice in their GSTR-1 / GSTR-2B portal yet.</p>
                                        </div>
                                    ) : (
                                        <div className="bg-indigo-50/40 p-4 rounded-xl border border-indigo-100 space-y-3">
                                            {/* Prominent Top Row: Period of GSTR & ITC Availability */}
                                            <div className="grid grid-cols-2 gap-3 pb-3 border-b border-indigo-100/80">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1 font-medium">Period of GSTR</div>
                                                    <div className="font-bold text-slate-800 text-sm">
                                                        {formatPeriod(selectedRow.gstr_period || selectedRow.raw_data?.fp || selectedRow.raw_data?.period, selectedMonth, selectedYear)}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1 font-medium">ITC Availability</div>
                                                    <div>
                                                        <span className={`inline-flex items-center px-2.5 py-1 text-xs font-bold rounded-full ${selectedRow.itc_availability === 'NO' || selectedRow.itc_availment === 'NO' || String(selectedRow.raw_data?.itcavl || '').toUpperCase() === 'N'
                                                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                                            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                                            }`}>
                                                            {selectedRow.itc_availability === 'NO' || selectedRow.itc_availment === 'NO' || String(selectedRow.raw_data?.itcavl || '').toUpperCase() === 'N'
                                                                ? '🚫 Ineligible (No ITC)'
                                                                : '✓ Eligible (ITC Available)'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Supplier GSTIN</div>
                                                <div className="font-mono text-sm font-semibold text-slate-800">{selectedRow.supplier_gstin || 'N/A'}</div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Number</div>
                                                    <div className="font-semibold text-slate-800">{selectedRow.invoice_no}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Date</div>
                                                    <div className="font-medium text-slate-800">{selectedRow.invoice_date}</div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                                    <div className="font-bold text-indigo-700">₹{Number(selectedRow.invoice_value || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Taxable Value</div>
                                                    <div className="font-medium text-slate-800">₹{Number(selectedRow.taxable_value || 0).toFixed(2)}</div>
                                                </div>
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
                                                <div className="text-xs text-slate-500 mb-1">Reverse Charge</div>
                                                <div className="font-medium text-slate-800">{selectedRow.reverse_charge || 'N'}</div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Books Data */}
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-teal-100">
                                        <div className="w-2 h-2 rounded-full bg-teal-500"></div>
                                        <h4 className="font-bold text-teal-900">Your Books (Purchase Invoices)</h4>
                                    </div>
                                    {selectedRow.books_data ? (
                                        <div className="bg-teal-50/40 p-4 rounded-xl border border-teal-100 space-y-3">
                                            {/* Prominent Top Row: Period of GSTR & ITC Availability */}
                                            <div className="grid grid-cols-2 gap-3 pb-3 border-b border-teal-100/80">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1 font-medium">Period of GSTR</div>
                                                    <div className="font-bold text-slate-800 text-sm">
                                                        {formatPeriod(selectedRow.books_data.gstr_period || `${selectedMonth} ${selectedYear}`, selectedMonth, selectedYear)}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1 font-medium">ITC Availability</div>
                                                    <div>
                                                        <span className={`inline-flex items-center px-2.5 py-1 text-xs font-bold rounded-full ${selectedRow.books_data.itc_availability === 'NO'
                                                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                                            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                                            }`}>
                                                            {selectedRow.books_data.itc_availability === 'NO' ? '🚫 Ineligible (No ITC)' : '✓ Eligible (ITC Available)'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Supplier GSTIN</div>
                                                <div className="font-mono text-sm font-semibold text-slate-800">{selectedRow.books_data.supplier_gstin || 'N/A'}</div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Number</div>
                                                    <div className="font-semibold text-slate-800">{selectedRow.books_data.invoice_no}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Date</div>
                                                    <div className="font-medium text-slate-800">{selectedRow.books_data.invoice_date}</div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                                    <div className="font-bold text-teal-700">₹{Number(selectedRow.books_data.invoice_value || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">Taxable Value</div>
                                                    <div className="font-medium text-slate-800">₹{Number(selectedRow.books_data.taxable_value || 0).toFixed(2)}</div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-3 gap-2">
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">IGST</div>
                                                    <div className="font-medium text-slate-800">₹{Number(selectedRow.books_data.igst || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">CGST</div>
                                                    <div className="font-medium text-slate-800">₹{Number(selectedRow.books_data.cgst || 0).toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-slate-500 mb-1">SGST</div>
                                                    <div className="font-medium text-slate-800">₹{Number(selectedRow.books_data.sgst || 0).toFixed(2)}</div>
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Reverse Charge</div>
                                                <div className="font-medium text-slate-800">{selectedRow.books_data.reverse_charge || 'N'}</div>
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
                                                            source: 'purchase_gstr2b_reco_drilldown',
                                                            returnTo: 'GST',
                                                            returnTab: 'GSTR2B_RECO',
                                                            preserveVoucherState: true
                                                        });
                                                        setSelectedRow(null);
                                                        setShowBulkErrorModal(false);
                                                    }
                                                }}
                                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-semibold transition-colors"
                                            >
                                                Create Purchase Voucher
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Validation Audit Matrix */}
                            {(() => {
                                const auditFields = (selectedRow.matching_details?.fields || []).filter((f: any) => f.field !== 'Total Value');
                                if (auditFields.length === 0) return null;
                                return (
                                    <div className="border-t border-slate-100 pt-4">
                                        <h4 className="text-sm font-bold text-slate-800 mb-3">{auditFields.length}-Field Validation Audit</h4>
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
                                                    {auditFields.map((f: any, idx: number) => (
                                                        <tr key={idx} className={f.status === 'MISMATCH' || f.status === 'BLOCKED' ? 'bg-rose-50/50' : ''}>
                                                            <td className="p-2 font-medium text-slate-800">{f.field}</td>
                                                            <td className="p-2 text-indigo-700">{typeof f.gstr2b === 'number' ? `₹${f.gstr2b.toFixed(2)}` : String(f.gstr2b ?? 'N/A')}</td>
                                                            <td className="p-2 text-teal-700">{typeof f.books === 'number' ? `₹${f.books.toFixed(2)}` : String(f.books ?? 'N/A')}</td>
                                                            <td className="p-2 text-slate-600">{f.difference !== undefined ? `₹${Number(f.difference).toFixed(2)}` : '-'}</td>
                                                            <td className="p-2">
                                                                <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${f.status === 'MATCH' ? 'bg-emerald-100 text-emerald-800' :
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
                                );
                            })()}
                        </div>
                        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center gap-3">
                            <div>
                                {selectedRow?.books_data?.purchase_voucher_id && (
                                    <button
                                        onClick={() => {
                                            if (onNavigate) {
                                                const voucherPayload = {
                                                    id: selectedRow.books_data.purchase_voucher_id,
                                                    voucherNo: selectedRow.books_data.invoice_no,
                                                    type: 'Purchase',
                                                    source: 'purchase_gstr2b_reco_drilldown',
                                                    returnTo: 'GST',
                                                    returnTab: 'GSTR2B_RECO',
                                                    gstr2b_invoice_date: selectedRow.invoice_date,
                                                    gstr2b_invoice_no: selectedRow.invoice_no,
                                                    gstr2b_invoice_value: selectedRow.invoice_value,
                                                    gstr2b_gstin: selectedRow.supplier_gstin,
                                                    gstr2b_vendor_name: selectedRow.vendor_name,
                                                };
                                                if (setViewVoucherData) {
                                                    setViewVoucherData(voucherPayload);
                                                }
                                                // Keep bulk review state active in sessionStorage so returning re-opens the bulk review screen
                                                try {
                                                    sessionStorage.setItem('reco_bulk_review_open', 'true');
                                                    sessionStorage.setItem('reco_selected_partial_ids', JSON.stringify(selectedPartialIds));
                                                } catch { }
                                                setSelectedRow(null);
                                                onNavigate('Vouchers', {
                                                    viewVoucher: voucherPayload,
                                                    returnTo: 'GST',
                                                    returnTab: 'GSTR2B_RECO',
                                                    returnBulkReview: true,
                                                    preserveVoucherState: true
                                                });
                                            }
                                        }}
                                        className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded shadow text-sm font-semibold transition-all flex items-center gap-2 cursor-pointer"
                                    >
                                        ✏️ Open Purchase Voucher to Fix
                                    </button>
                                )}
                            </div>
                            <div className="flex gap-3 items-center">
                                <button onClick={() => setSelectedRow(null)} className="px-4 py-2 text-slate-600 hover:text-slate-900 font-semibold text-sm transition-colors cursor-pointer">
                                    Close
                                </button>
                                {selectedRow.pushed_to_gstr3b ? (
                                    <span className="px-4 py-2 bg-teal-100 text-teal-800 rounded text-sm font-bold border border-teal-300 flex items-center gap-1.5 shadow-xs select-none">
                                        ✓ Pushed to GSTR-3B
                                    </span>
                                ) : (
                                    <button
                                        onClick={async () => {
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
                                            setIsPushing(true);
                                            try {
                                                const res: any = await httpClient.post('/api/gst/reconciliation/push_to_gstr3b/', {
                                                    month: selectedMonth,
                                                    year: selectedYear,
                                                    reconciliation_ids: [selectedRow.id],
                                                    force_accept: true
                                                });
                                                showSuccess(res.message || `Invoice ${selectedRow.invoice_no} accepted & pushed to GSTR-3B!`);
                                                setSelectedRow(null);
                                                setSelectedExactIds(prev => prev.filter(id => id !== selectedRow.id));
                                                await fetchResults();
                                            } catch (err: any) {
                                                showError(err.response?.data?.error || err.message || 'Failed to push to GSTR-3B.');
                                            } finally {
                                                setIsPushing(false);
                                            }
                                        }}
                                        disabled={isPushing}
                                        className={`px-4 py-2 text-white rounded shadow text-sm font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${isPushing ? 'bg-emerald-400 cursor-wait' : 'bg-emerald-600 hover:bg-emerald-700 active:scale-95'}`}
                                    >
                                        {isPushing ? 'Pushing...' : '✓ Accept & Push to GSTR-3B'}
                                    </button>
                                )}
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
                            <button onClick={() => setShowPushConfirmModal(false)} className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 cursor-pointer">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <p className="text-sm text-slate-600">
                                <span className="font-bold text-slate-900">{selectedExactCount}</span> exact-match invoices are selected for period <span className="font-semibold text-indigo-700">{selectedMonth} {selectedYear}</span>.
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
                                className="px-4 py-2 text-slate-600 hover:text-slate-900 font-semibold text-sm transition-colors cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handlePushToGSTR3B}
                                disabled={isPushing}
                                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded shadow text-sm font-semibold transition-all flex items-center gap-2 cursor-pointer"
                            >
                                {isPushing ? 'Pushing...' : 'Push to GSTR-3B'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Review Errors Modal */}
            {showBulkErrorModal && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl overflow-hidden flex flex-col max-h-[92vh] border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
                        {/* Modal Header */}
                        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-200 bg-slate-50/80">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center font-black text-lg shadow-sm">
                                    🔍
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-slate-900 tracking-tight">Partial / Mismatch Review</h3>
                                    <p className="text-xs font-medium text-slate-500">
                                        Error analysis for {selectedPartialRows.length} selected invoices ({selectedMonth} {selectedYear})
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => {
                                    setShowBulkErrorModal(false);
                                    setSelectedErrorKeys([]);
                                }}
                                className="p-2 text-slate-400 hover:text-slate-700 rounded-full hover:bg-slate-200/60 transition-colors cursor-pointer"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 overflow-y-auto space-y-6 flex-1 bg-slate-50/30">
                            {/* Aggregated Mismatch Summary with Multi-Select Bulk Filtering */}
                            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                                <div className="flex flex-wrap justify-between items-center gap-2">
                                    <div className="flex items-center gap-2">
                                        <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-2">
                                            <span>📊 MISMATCH SUMMARY</span>
                                        </h4>
                                        <span className="text-[11px] font-medium text-slate-500">
                                            (Select one or multiple error types to filter invoices)
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={selectAllErrorCategories}
                                            className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded text-xs font-bold transition-all cursor-pointer flex items-center gap-1"
                                            title="Select all error types with affected invoices"
                                        >
                                            <span>☑ Select All Errors</span>
                                        </button>
                                        {selectedErrorKeys.length > 0 && (
                                            <button
                                                onClick={clearAllErrorCategories}
                                                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded text-xs font-bold transition-all cursor-pointer flex items-center gap-1"
                                                title="Clear all error selections"
                                            >
                                                <span>✕ Clear Filters ({selectedErrorKeys.length})</span>
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
                                    {categoryCounts.map(cat => {
                                        const isSelected = selectedErrorKeys.includes(cat.key);
                                        return (
                                            <button
                                                key={cat.key}
                                                onClick={() => toggleErrorCategory(cat.key)}
                                                className={`flex items-center justify-between p-2.5 rounded-lg border text-left transition-all cursor-pointer ${isSelected
                                                    ? 'bg-indigo-50/90 border-indigo-500 ring-2 ring-indigo-500/30 shadow-sm text-indigo-900 font-bold'
                                                    : cat.count > 0
                                                        ? 'bg-slate-50 hover:bg-indigo-50/40 border-slate-200 hover:border-indigo-300 text-slate-700 font-semibold'
                                                        : 'bg-slate-50/40 border-slate-100 text-slate-400 opacity-50 cursor-not-allowed'
                                                    }`}
                                                disabled={cat.count === 0}
                                            >
                                                <div className="flex items-center gap-2 min-w-0">
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected}
                                                        onChange={() => { }}
                                                        disabled={cat.count === 0}
                                                        className="rounded text-indigo-600 focus:ring-indigo-500 h-3.5 w-3.5 shrink-0 pointer-events-none"
                                                    />
                                                    <span className="text-xs leading-tight truncate" title={cat.label}>
                                                        {cat.shortLabel || cat.label}
                                                    </span>
                                                </div>
                                                <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${isSelected
                                                    ? 'bg-indigo-600 text-white'
                                                    : cat.count > 0
                                                        ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                                        : 'bg-slate-100 text-slate-400'
                                                    }`}>
                                                    {cat.count}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Selected Summary Info Bar */}
                            <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-slate-600">
                                <div className="flex items-center gap-4">
                                    <div>Selected Invoices: <strong className="text-slate-900 font-bold">{selectedPartialRows.length}</strong></div>
                                    <div className="w-1 h-1 rounded-full bg-slate-300"></div>
                                    <div>Invoices With Errors: <strong className="text-rose-700 font-bold">{selectedPartialRows.filter(r => (r.mismatches || []).length > 0 || r.status === 'PARTIAL' || r.status === 'MISMATCH').length}</strong></div>
                                </div>
                                {selectedErrorKeys.length > 0 && (
                                    <div className="flex flex-wrap items-center gap-1.5">
                                        <span className="text-xs text-slate-500 font-medium">Active Filters:</span>
                                        {selectedErrorKeys.map(k => {
                                            const cat = MISMATCH_CATEGORIES.find(c => c.key === k);
                                            return (
                                                <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 font-semibold text-[11px]">
                                                    <span>{cat?.shortLabel || cat?.label || k}</span>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            toggleErrorCategory(k);
                                                        }}
                                                        className="hover:text-indigo-950 font-bold cursor-pointer"
                                                        title="Remove this error filter"
                                                    >
                                                        ✕
                                                    </button>
                                                </span>
                                            );
                                        })}
                                        <span className="ml-1 bg-indigo-200 text-indigo-900 px-2 py-0.5 rounded-full text-[11px] font-bold">
                                            {modalFilteredInvoices.length} of {selectedPartialRows.length} shown
                                        </span>
                                    </div>
                                )}
                            </div>

                            {/* Individual Invoice Error Cards */}
                            <div className="space-y-5">
                                {modalFilteredInvoices.length === 0 ? (
                                    <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500">
                                        <p className="text-sm font-semibold">No invoices match the selected error category.</p>
                                        <button
                                            onClick={clearAllErrorCategories}
                                            className="mt-2 text-xs text-indigo-600 font-bold underline cursor-pointer"
                                        >
                                            View all {selectedPartialRows.length} selected invoices
                                        </button>
                                    </div>
                                ) : (
                                    modalFilteredInvoices.map((inv, invIdx) => {
                                        const fields = getInvoiceValidationFields(inv);
                                        const activeMismatches = (inv.mismatches || []).filter((m: string) => m.toUpperCase() !== 'TOTAL VALUE MISMATCH');

                                        return (
                                            <div key={inv.id || invIdx} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-all hover:border-indigo-300">
                                                {/* Invoice Header */}
                                                <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                                                    <div className="flex flex-wrap items-center gap-3">
                                                        <span className="px-2.5 py-1 bg-indigo-600 text-white rounded text-xs font-black tracking-wide">
                                                            {inv.invoice_no || inv.books_data?.invoice_no}
                                                        </span>
                                                        <span className="font-bold text-slate-800 text-sm">
                                                            {inv.vendor_name || inv.books_data?.vendor_name || 'Vendor'}
                                                        </span>
                                                        <span className="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                                            GSTIN: {inv.supplier_gstin || inv.books_data?.supplier_gstin}
                                                        </span>
                                                        <span className="text-xs text-slate-600 font-medium">
                                                            Date: {inv.invoice_date || inv.books_data?.invoice_date}
                                                        </span>
                                                        <span className="text-xs font-bold text-slate-900">
                                                            Value: ₹{Number(inv.invoice_value || inv.books_data?.invoice_value || 0).toFixed(2)}
                                                        </span>
                                                    </div>

                                                    <div className="flex items-center gap-3">
                                                        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded text-xs font-bold text-amber-800">
                                                            <span>Match:</span>
                                                            <span>{inv.matching_score}%</span>
                                                        </div>
                                                        <button
                                                            onClick={() => setSelectedRow(inv)}
                                                            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer active:scale-95"
                                                            title="Open detailed review and fix voucher"
                                                        >
                                                            <span>🔍</span>
                                                            <span>REVIEW</span>
                                                        </button>
                                                    </div>
                                                </div>

                                                {/* Detected Mismatches Badges */}
                                                {activeMismatches.length > 0 && (
                                                    <div className="px-4 py-2.5 bg-rose-50/60 border-b border-rose-100 flex flex-wrap items-center gap-2">
                                                        <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">Detected Issues:</span>
                                                        {activeMismatches.map((m: string, mi: number) => (
                                                            <span key={mi} className="inline-flex items-center gap-1 px-2 py-0.5 bg-rose-100 text-rose-800 rounded text-xs font-semibold border border-rose-200">
                                                                ⚠️ {m}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* 12-Field Side-by-Side Comparison Table */}
                                                <div className="overflow-x-auto">
                                                    <table className="w-full text-left text-xs border-collapse">
                                                        <thead>
                                                            <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 uppercase font-black text-[10px] tracking-wider">
                                                                <th className="py-2.5 px-4">Validation Field</th>
                                                                <th className="py-2.5 px-4 text-indigo-900 bg-indigo-50/40">Government Data (GSTR-2B)</th>
                                                                <th className="py-2.5 px-4 text-slate-800 bg-slate-50/40">Your Books (Purchase Voucher)</th>
                                                                <th className="py-2.5 px-4 text-right">Difference</th>
                                                                <th className="py-2.5 px-4 text-center">Status</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-slate-100">
                                                            {fields.map((f: any, fi: number) => {
                                                                const isMismatch = f.status === 'MISMATCH' || f.status === 'BLOCKED';
                                                                const diffVal = f.difference !== undefined ? Number(f.difference) : null;

                                                                return (
                                                                    <tr key={fi} className={`hover:bg-slate-50/80 transition-colors ${isMismatch ? 'bg-rose-50/20' : ''}`}>
                                                                        <td className="py-2 px-4 font-semibold text-slate-700">
                                                                            {f.field}
                                                                        </td>
                                                                        <td className="py-2 px-4 font-mono font-medium text-indigo-900 bg-indigo-50/20">
                                                                            {typeof f.gstr2b === 'number' ? `₹${f.gstr2b.toFixed(2)}` : String(f.gstr2b ?? '-')}
                                                                        </td>
                                                                        <td className="py-2 px-4 font-mono font-medium text-slate-800 bg-slate-50/20">
                                                                            {typeof f.books === 'number' ? `₹${f.books.toFixed(2)}` : String(f.books ?? '-')}
                                                                        </td>
                                                                        <td className="py-2 px-4 font-mono text-right font-semibold">
                                                                            {diffVal !== null ? (
                                                                                <span className={Math.abs(diffVal) > 0.01 ? 'text-rose-600 font-bold' : 'text-slate-400'}>
                                                                                    {Math.abs(diffVal) > 0.01 ? `${diffVal > 0 ? '+' : ''}₹${diffVal.toFixed(2)}` : '₹0.00'}
                                                                                </span>
                                                                            ) : '-'}
                                                                        </td>
                                                                        <td className="py-2 px-4 text-center">
                                                                            {f.status === 'MATCH' ? (
                                                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                                                                    ✓ MATCH
                                                                                </span>
                                                                            ) : f.status === 'BLOCKED' ? (
                                                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                                                                                    ⚠ BLOCKED
                                                                                </span>
                                                                            ) : (
                                                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                                                                                    ✗ MISMATCH
                                                                                </span>
                                                                            )}
                                                                        </td>
                                                                    </tr>
                                                                );
                                                            })}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="p-4 border-t border-slate-200 bg-slate-50/90 flex flex-wrap justify-between items-center gap-3">
                            <div className="text-xs text-slate-500 max-w-2xl">
                                💡 Click <strong>REVIEW</strong> on any invoice to open the voucher editor and fix differences. After re-running reconciliation, validated invoices will automatically become <strong>EXACT MATCH</strong> and eligible for GSTR-3B push.
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => {
                                        setShowBulkErrorModal(false);
                                        setSelectedErrorKeys([]);
                                        try {
                                            sessionStorage.removeItem('reco_bulk_review_open');
                                        } catch { }
                                    }}
                                    className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-bold text-xs shadow-sm transition-all cursor-pointer"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
