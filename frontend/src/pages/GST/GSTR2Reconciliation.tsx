import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';
import { apiService } from '../../services/api';
import { showSuccess, showError } from '../../utils/toast';

export default function GSTR2Reconciliation({ onNavigate, setViewVoucherData }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void }) {
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
        fetchResults();
    }, [selectedMonth, selectedYear]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        try {
            // In a real app, read file and send to API
            // For now, simulate upload
            const reader = new FileReader();
            reader.onload = async (event) => {
                const text = event.target?.result as string;
                try {
                    const json = JSON.parse(text);
                    await httpClient.post('/api/gst/reconciliation/upload_2b/', json);
                    showSuccess('GSTR-2B Ingested successfully');
                } catch (e) {
                    showError('Invalid JSON file');
                }
            };
            reader.readAsText(file);
        } finally {
            setIsLoading(false);
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
                    <div className="p-4 bg-orange-50 rounded-[4px] border border-orange-100">
                        <span className="text-sm text-orange-700 font-medium">Partial Match</span>
                        <div className="text-2xl font-bold text-orange-900">{summary.partial_match}</div>
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

                <div className="mb-2">
                    <h3 className="text-sm font-semibold text-gray-700">Currently viewing GSTR-2B data for: {selectedMonth} {selectedYear}</h3>
                </div>
                <div className="erp-table-container">
                    <table className="erp-table">
                        <thead>
                            <tr>
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
                                    <td colSpan={7} className="text-center py-10 text-slate-400">
                                        No reconciliation data found. Click "Fetch from Sandbox API" to begin.
                                    </td>
                                </tr>
                            ) : (
                                results.map((row, idx) => (
                                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                        <td>
                                            <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full 
                                                ${row.status === 'EXACT' ? 'bg-emerald-100 text-emerald-800' :
                                                  row.status === 'PARTIAL' ? 'bg-orange-100 text-orange-800' :
                                                  row.status === 'MISSING_BOOKS' ? 'bg-rose-100 text-rose-800' :
                                                  'bg-slate-100 text-slate-800'}`}>
                                                {row.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td className="font-medium text-slate-800">{row.supplier_gstin}</td>
                                        <td>{row.invoice_no}</td>
                                        <td>{row.invoice_date}</td>
                                        <td className="font-semibold">₹{Number(row.invoice_value).toFixed(2)}</td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
                                                    <div 
                                                        className={`h-full ${row.matching_score >= 70 ? 'bg-emerald-500' : row.matching_score >= 50 ? 'bg-orange-500' : 'bg-rose-500'}`} 
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
                        <div className="p-6 overflow-y-auto">
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
                                            <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                            <div className="font-bold text-indigo-700">₹{Number(selectedRow.invoice_value).toFixed(2)}</div>
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
                                                <div className={`font-medium ${selectedRow.books_data.vendor_name !== selectedRow.vendor_name ? 'text-orange-600 bg-orange-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.vendor_name || 'N/A'}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Supplier GSTIN</div>
                                                <div className="font-medium text-slate-800">{selectedRow.supplier_gstin}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Number</div>
                                                <div className={`font-medium ${selectedRow.books_data.invoice_no?.toLowerCase() !== selectedRow.invoice_no?.toLowerCase() ? 'text-orange-600 bg-orange-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.invoice_no}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Date</div>
                                                <div className={`font-medium ${selectedRow.books_data.invoice_date !== selectedRow.invoice_date ? 'text-orange-600 bg-orange-50 px-1 rounded' : 'text-slate-800'}`}>{selectedRow.books_data.invoice_date}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-slate-500 mb-1">Invoice Value</div>
                                                <div className={`font-bold ${Number(selectedRow.books_data.invoice_value) !== Number(selectedRow.invoice_value) ? 'text-orange-600 bg-orange-50 px-1 rounded' : 'text-teal-700'}`}>₹{Number(selectedRow.books_data.invoice_value).toFixed(2)}</div>
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
                                                });
                                                setSelectedRow(null);
                                                onNavigate('Vouchers');
                                            }
                                        }}
                                        className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded shadow text-sm font-semibold transition-all flex items-center gap-2"
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
        </div>
    );
}
