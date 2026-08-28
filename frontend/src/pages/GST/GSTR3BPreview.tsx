import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';
import FileGSTR3BModal from './FileGSTR3BModal';
import { Wallet, CheckCircle } from 'lucide-react';
import { formatDate } from '../../utils/formatting';

export default function GSTR3BPreview({ onNavigate, setActiveTab }: { onNavigate?: (page: string, params?: any) => void; setActiveTab?: (tab: string) => void }) {
    const [isLoading, setIsLoading] = useState(false);
    const [report, setReport] = useState<any>(null);
    const [selectedMonth, setSelectedMonth] = useState('January');
    const [selectedYear, setSelectedYear] = useState('2024-25');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [ledgerBalances, setLedgerBalances] = useState<any>(null);
    const [isFiled, setIsFiled] = useState(false);

    const fetch3B = async () => {
        setIsLoading(true);
        try {
            const res: any = await httpClient.get(`/api/gst/reconciliation/gstr3b_preview/?month=${selectedMonth}&year=${selectedYear}`);
            setReport(res);
            setIsFiled(res.status === 'FILED');
        } finally {
            setIsLoading(false);
        }
    };

    const fetchLedgers = async () => {
        try {
            const res: any = await httpClient.get('/api/gst/reconciliation/fetch_ledger_balances/');
            setLedgerBalances(res.data || res);
        } catch (err) {
            console.error('Failed to fetch ledger balances', err);
        }
    };

    useEffect(() => {
        fetch3B();
        fetchLedgers();
        setIsFiled(false); // reset filing status on period change
    }, [selectedMonth, selectedYear]);

    return (
        <div className="space-y-6">
            <div className="erp-container">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="section-title border-none pb-0">GSTR-3B Monthly Summary</h2>
                        <p className="helper-text mb-4">Liability and ITC computation for {selectedMonth} {selectedYear}</p>
                        <div className="flex gap-4 items-center bg-indigo-50/50 p-2 rounded border border-indigo-100 w-fit">
                            <span className="text-sm font-semibold text-indigo-900">Period:</span>
                            <select 
                                value={selectedMonth} 
                                onChange={(e) => setSelectedMonth(e.target.value)}
                                className="px-3 py-1.5 border border-indigo-200 rounded text-sm bg-white focus:ring-1 focus:ring-indigo-500"
                            >
                                {['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'].map(m => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                            <select 
                                value={selectedYear} 
                                onChange={(e) => setSelectedYear(e.target.value)}
                                className="px-3 py-1.5 border border-indigo-200 rounded text-sm bg-white focus:ring-1 focus:ring-indigo-500"
                            >
                                {['2023-24', '2024-25', '2025-26', '2026-27'].map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="space-y-4">
                    {/* Liability */}
                    <div className="border rounded-[4px] overflow-hidden">
                        <div className="bg-slate-50 p-3 border-b font-semibold">3.1 Details of Outward Supplies (from GSTR-1)</div>
                        <div className="p-4 grid grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <label className="text-xs text-slate-500 uppercase font-bold">IGST</label>
                                <div className="text-lg font-mono">₹{report?.output_tax_igst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-slate-500 uppercase font-bold">CGST</label>
                                <div className="text-lg font-mono">₹{report?.output_tax_cgst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-slate-500 uppercase font-bold">SGST</label>
                                <div className="text-lg font-mono">₹{report?.output_tax_sgst || '0.00'}</div>
                            </div>
                        </div>
                    </div>

                    {/* ITC */}
                    <div className="border rounded-[4px] overflow-hidden">
                        <div className="bg-indigo-50 p-3 border-b font-semibold text-indigo-900 flex justify-between items-center flex-wrap gap-2">
                            <span>4. Eligible ITC (from Reconciliation)</span>
                            {report?.pushed_count > 0 ? (
                                <span className="text-xs font-bold bg-teal-100 text-teal-800 px-3 py-1 rounded-full border border-teal-300 shadow-xs">
                                    ✓ {report.pushed_count} Invoices Reconciled & Pushed (Total ITC: ₹{Number(report.total_eligible_itc || (parseFloat(report.input_tax_igst || '0') + parseFloat(report.input_tax_cgst || '0') + parseFloat(report.input_tax_sgst || '0'))).toFixed(2)})
                                </span>
                            ) : (
                                <span className="text-xs font-medium text-slate-500 bg-white px-2.5 py-1 rounded border border-slate-200">
                                    0 Invoices Pushed
                                </span>
                            )}
                        </div>
                        <div className="p-4 grid grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <label className="text-xs text-indigo-500 uppercase font-bold">IGST</label>
                                <div className="text-lg font-mono">₹{report?.input_tax_igst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-indigo-500 uppercase font-bold">CGST</label>
                                <div className="text-lg font-mono">₹{report?.input_tax_cgst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-indigo-500 uppercase font-bold">SGST</label>
                                <div className="text-lg font-mono">₹{report?.input_tax_sgst || '0.00'}</div>
                            </div>
                        </div>

                        {/* Breakdown Table of Pushed GSTR-2B Invoices */}
                        {report?.pushed_invoices && report.pushed_invoices.length > 0 ? (
                            <div className="border-t border-indigo-100 bg-indigo-50/20 p-4">
                                <div className="text-xs font-bold text-indigo-900 uppercase tracking-wider mb-2 flex items-center justify-between">
                                    <span>📄 Reconciled Invoices Contributing to Eligible ITC ({report.pushed_invoices.length})</span>
                                    <span className="text-[11px] font-semibold text-teal-700">Source: GSTR-2B Auto-Reconciliation</span>
                                </div>
                                <div className="overflow-x-auto rounded border border-indigo-200/60 bg-white shadow-xs">
                                    <table className="w-full text-left text-xs">
                                        <thead className="bg-indigo-50/80 text-indigo-900 font-semibold border-b border-indigo-100">
                                            <tr>
                                                <th className="p-2.5">Invoice No</th>
                                                <th className="p-2.5">Supplier GSTIN</th>
                                                <th className="p-2.5">Date</th>
                                                <th className="p-2.5 text-right">Taxable Val</th>
                                                <th className="p-2.5 text-right">IGST</th>
                                                <th className="p-2.5 text-right">CGST</th>
                                                <th className="p-2.5 text-right">SGST</th>
                                                <th className="p-2.5 text-right">Total ITC</th>
                                                <th className="p-2.5 text-center">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {report.pushed_invoices.map((inv: any, i: number) => (
                                                <tr key={i} className="hover:bg-indigo-50/30 transition-colors">
                                                    <td className="p-2.5 font-bold text-slate-800">{inv.invoice_no}</td>
                                                    <td className="p-2.5 font-mono text-slate-600">{inv.supplier_gstin}</td>
                                                    <td className="p-2.5 text-slate-600">{inv.invoice_date}</td>
                                                    <td className="p-2.5 text-right font-mono">₹{Number(inv.taxable_value).toFixed(2)}</td>
                                                    <td className="p-2.5 text-right font-mono text-indigo-700">₹{Number(inv.igst).toFixed(2)}</td>
                                                    <td className="p-2.5 text-right font-mono text-indigo-700">₹{Number(inv.cgst).toFixed(2)}</td>
                                                    <td className="p-2.5 text-right font-mono text-indigo-700">₹{Number(inv.sgst).toFixed(2)}</td>
                                                    <td className="p-2.5 text-right font-mono font-bold text-emerald-700">
                                                        ₹{(Number(inv.igst) + Number(inv.cgst) + Number(inv.sgst)).toFixed(2)}
                                                    </td>
                                                    <td className="p-2.5 text-center">
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal-100 text-teal-800 border border-teal-200">
                                                            ✓ Pushed
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : (
                            <div className="border-t border-indigo-100 bg-slate-50/50 p-4 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                                <span>No GSTR-2B invoices pushed for this period yet.</span>
                                {setActiveTab && (
                                    <button
                                        onClick={() => setActiveTab('GSTR2B_RECO')}
                                        className="font-bold text-indigo-600 hover:text-indigo-800 underline cursor-pointer"
                                    >
                                        Go to GSTR-2B Reconciliation →
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Payable */}
                    <div className="border rounded-[4px] overflow-hidden bg-slate-900 text-white">
                        <div className="p-3 border-b border-white/10 font-semibold">Net Tax Payable (After ITC Offset)</div>
                        <div className="p-4 grid grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <label className="text-xs text-slate-400 uppercase font-bold">IGST Payable</label>
                                <div className="text-xl font-bold text-emerald-400">₹{report?.net_igst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-slate-400 uppercase font-bold">CGST Payable</label>
                                <div className="text-xl font-bold text-emerald-400">₹{report?.net_cgst || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-slate-400 uppercase font-bold">SGST Payable</label>
                                <div className="text-xl font-bold text-emerald-400">₹{report?.net_sgst || '0.00'}</div>
                            </div>
                        </div>
                    </div>
                    
                    {/* Electronic Ledgers */}
                    <div className="border border-blue-200 rounded-[4px] overflow-hidden bg-blue-50/30">
                        <div className="bg-blue-100/50 p-3 border-b border-blue-200 font-semibold flex items-center gap-2 text-blue-900">
                            <Wallet className="w-5 h-5 text-blue-600" />
                            Electronic Ledger Balances
                        </div>
                        <div className="p-4 grid grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <label className="text-xs text-blue-500 uppercase font-bold">Cash Ledger</label>
                                <div className="text-xl font-bold text-blue-700">₹{ledgerBalances?.cash_balance?.toFixed(2) || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-blue-500 uppercase font-bold">Credit Ledger (IGST)</label>
                                <div className="text-lg font-mono text-blue-800">₹{ledgerBalances?.credit_balance_igst?.toFixed(2) || '0.00'}</div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs text-blue-500 uppercase font-bold">Liability Ledger</label>
                                <div className="text-lg font-mono text-blue-800">₹{ledgerBalances?.liability_balance?.toFixed(2) || '0.00'}</div>
                            </div>
                        </div>
                    </div>

                    {/* Action Bar */}
                    <div className="flex justify-end pt-4 border-t mt-6">
                        {isFiled ? (
                            <div className="flex flex-col items-end gap-2">
                                <div className="flex items-center gap-2 text-green-600 font-bold bg-green-50 px-6 py-3 rounded-lg border border-green-200">
                                    <CheckCircle className="w-6 h-6" />
                                    RETURN FILED SUCCESSFULLY
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={() => setIsModalOpen(true)}
                                className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold shadow-lg shadow-indigo-200 transition-all active:scale-95"
                            >
                                FILE GSTR-3B
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Filing History Section */}
            {isFiled && report?.arn_number && (
                <div className="erp-container mt-6">
                    <h3 className="section-title">Filing History & Receipts</h3>
                    <div className="overflow-x-auto">
                        <table className="erp-table">
                            <thead>
                                <tr>
                                    <th>Return Type</th>
                                    <th>Period</th>
                                    <th>Status</th>
                                    <th>ARN Number</th>
                                    <th>Filed On</th>
                                    <th className="text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td className="font-semibold text-slate-800">GSTR-3B</td>
                                    <td>{selectedMonth} {selectedYear}</td>
                                    <td>
                                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">
                                            FILED
                                        </span>
                                    </td>
                                    <td className="font-mono text-sm text-slate-600">{report.arn_number}</td>
                                    <td>{formatDate(report.filed_date)}</td>
                                    <td className="text-right">
                                        <button onClick={() => window.print()} className="text-indigo-600 hover:text-indigo-800 font-semibold text-sm">
                                            Download PDF
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            <FileGSTR3BModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                month={selectedMonth}
                year={selectedYear}
                netTaxPayable={
                    parseFloat(report?.net_igst || '0') + 
                    parseFloat(report?.net_cgst || '0') + 
                    parseFloat(report?.net_sgst || '0')
                }
                cashBalance={ledgerBalances?.cash_balance || 0}
                onSuccess={() => {
                    setIsModalOpen(false);
                    setIsFiled(true);
                    fetch3B(); // Fetch the new ARN number and status from the server
                    fetchLedgers(); // Refresh balances
                }}
            />
        </div>
    );
}
