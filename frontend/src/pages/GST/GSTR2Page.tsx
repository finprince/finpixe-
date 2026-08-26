import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';

let savedPeriod: { year: string; month: string } | null = null;
let savedSubTab: string = 'B2B';
// Source selector state persisted across re-renders (module-level singleton)
let savedSourceTab: 'ITC_IN_BOOKS' | 'GSTR2B' = 'ITC_IN_BOOKS';

export default function GSTR2Page({ onNavigate, setViewVoucherData }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void }) {
    // ── Source selector (ITC IN BOOKS vs GSTR-2B) ────────────────────────────
    const [activeSourceTab, setActiveSourceTabState] = useState<'ITC_IN_BOOKS' | 'GSTR2B'>(savedSourceTab);
    const setActiveSourceTab = (tab: 'ITC_IN_BOOKS' | 'GSTR2B') => {
        savedSourceTab = tab;
        setActiveSourceTabState(tab);
    };

    // ── Sub-tabs state (B2B, B2BUR, IMPG, CDNR, CDNUR) ──────────────────────
    const [activeSubTab, setActiveSubTabState] = useState(savedSubTab);
    const activeTabRef = React.useRef<HTMLButtonElement | null>(null);
    const setActiveSubTab = (tab: string) => { savedSubTab = tab; setActiveSubTabState(tab); };

    useEffect(() => {
        if (activeTabRef.current) {
            activeTabRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    }, [activeSubTab]);

    const [period, setPeriodState] = useState(() => {
        if (savedPeriod) return savedPeriod;
        const today = new Date();
        const currentYear = today.getFullYear();
        const currentMonth = today.getMonth();
        const fyStartYear = currentMonth >= 3 ? currentYear : currentYear - 1;
        const months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        const currentMonthName = months[currentMonth] || 'January';
        return {
            year: `${fyStartYear}-${(fyStartYear + 1).toString().slice(-2)}`,
            month: currentMonthName
        };
    });

    const setPeriod = (newVal: { year: string; month: string }) => {
        savedPeriod = newVal;
        setPeriodState(newVal);
    };

    const [isLoading, setIsLoading] = useState(false);

    // ── ITC IN BOOKS data states (from Books / accounting vouchers) ──────────
    const [b2bData, setB2bData] = useState<any[]>([]);
    const [b2burData, setB2burData] = useState<any[]>([]);
    const [impgData, setImpgData] = useState<any[]>([]);
    const [cdnrData, setCdnrData] = useState<any[]>([]);
    const [cdnurData, setCdnurData] = useState<any[]>([]);
    const [stats, setStats] = useState<Record<string, number>>({});

    // ── GSTR-2B government data states (from GSTR2BInvoice model) ─────────────
    const [gstr2bInvoices, setGstr2bInvoices] = useState<any[]>([]);
    const [gstr2bLoading, setGstr2bLoading] = useState(false);
    const [gstr2bTotal, setGstr2bTotal] = useState(0);

    const subTabs = ['B2B', 'B2BUR', 'IMPG', 'CDNR', 'CDNUR'];

    // ── Fetch Books inward data ──────────────────────────────────────────────
    const fetchData = async () => {
        setIsLoading(true);
        try {
            let queryParams = new URLSearchParams(period as any).toString();
            const statsRes = await httpClient.get<Record<string, number>>(`/api/gst/gstr2/stats/?${queryParams}`);
            setStats(statsRes || {});

            const endpointMap: Record<string, string> = {
                'B2B': '/api/gst/gstr2/b2b/',
                'B2BUR': '/api/gst/gstr2/b2bur/',
                'IMPG': '/api/gst/gstr2/impg/',
                'CDNR': '/api/gst/gstr2/cdnr/',
                'CDNUR': '/api/gst/gstr2/cdnur/',
            };

            const url = endpointMap[activeSubTab];
            if (!url) {
                setIsLoading(false);
                return;
            }

            const fullUrl = `${url}?${queryParams}`;
            const response = await httpClient.get<any[]>(fullUrl);

            switch (activeSubTab) {
                case 'B2B': setB2bData(response || []); break;
                case 'B2BUR': setB2burData(response || []); break;
                case 'IMPG': setImpgData(response || []); break;
                case 'CDNR': setCdnrData(response || []); break;
                case 'CDNUR': setCdnurData(response || []); break;
            }
        } catch (error) {
            console.error('Failed to fetch GSTR2 books data', error);
        } finally {
            setIsLoading(false);
        }
    };

    // ── Fetch GSTR-2B government data ─────────────────────────────────────────
    const fetchGstr2bData = async () => {
        setGstr2bLoading(true);
        try {
            const params = new URLSearchParams({ month: period.month, year: period.year }).toString();
            const res = await httpClient.get<any>(`/api/gst/reconciliation/invoices/?${params}`);
            setGstr2bInvoices(res?.invoices || []);
            setGstr2bTotal(res?.count || 0);
        } catch (error) {
            console.error('Failed to fetch GSTR-2B government invoices', error);
            setGstr2bInvoices([]);
            setGstr2bTotal(0);
        } finally {
            setGstr2bLoading(false);
        }
    };

    useEffect(() => {
        if (activeSourceTab === 'ITC_IN_BOOKS') {
            fetchData();
        }
    }, [activeSubTab, period, activeSourceTab]);

    useEffect(() => {
        if (activeSourceTab === 'GSTR2B') {
            fetchGstr2bData();
        }
    }, [period, activeSourceTab]);

    const handleRowClick = (row: any, type: string) => {
        if (setViewVoucherData && onNavigate) {
            setViewVoucherData({
                ...row,
                voucherNo: row.invoice_no || row.note_no || row.boe_no,
                type: type,
                source: type === 'Purchase' ? 'purchase_gstr2_drilldown' : 'debitnote_gstr2_drilldown'
            });
            onNavigate('Vouchers');
        }
    };

    // ── Shared Period Controls (Financial Year, Month, Generate Return) ─────
    const renderPeriodControls = (onGenerate: () => void, isGenerating: boolean) => (
        <div className="erp-container shadow-sm">
            <div className="flex flex-wrap items-end gap-6">
                <div className="w-48">
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Financial Year</label>
                    <select
                        value={period.year}
                        onChange={(e) => setPeriod({ ...period, year: e.target.value })}
                        className="erp-select"
                    >
                        {(() => {
                            const years = [];
                            const today = new Date();
                            const currentYear = today.getFullYear();
                            const currentMonth = today.getMonth();
                            let fyStartYear = currentMonth >= 3 ? currentYear : currentYear - 1;
                            for (let i = 0; i < 11; i++) {
                                const start = fyStartYear - i;
                                const end = (start + 1).toString().slice(-2);
                                const fyLabel = `${start}-${end}`;
                                years.push(<option key={fyLabel} value={fyLabel}>{fyLabel}</option>);
                            }
                            return years;
                        })()}
                    </select>
                </div>
                <div className="w-48">
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Month</label>
                    <select
                        value={period.month}
                        onChange={(e) => setPeriod({ ...period, month: e.target.value })}
                        className="erp-select"
                    >
                        <option>January</option>
                        <option>February</option>
                        <option>March</option>
                        <option>April</option>
                        <option>May</option>
                        <option>June</option>
                        <option>July</option>
                        <option>August</option>
                        <option>September</option>
                        <option>October</option>
                        <option>November</option>
                        <option>December</option>
                    </select>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={onGenerate}
                        className="erp-button-primary"
                        disabled={isGenerating}
                    >
                        {isGenerating ? 'Generating...' : 'Generate Return'}
                    </button>
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Sticky Header Controls & Tabs */}
            <div className="sticky top-[49px] z-20 bg-[#FAFAFA] pt-1 pb-2 space-y-4">

                {/* ── Source Options Selector: [ ITC IN BOOKS ] [ GSTR-2B ] ── */}
                <div className="erp-container p-0 shadow-sm overflow-hidden">
                    <div
                        className="erp-tab-container mb-0 border-b border-slate-200 px-6 overflow-x-auto select-none bg-white flex items-center justify-between"
                        onWheel={(e) => {
                            if (e.deltaY !== 0) {
                                e.currentTarget.scrollLeft += e.deltaY;
                            }
                        }}
                    >
                        <div className="flex items-center">
                            <button
                                onClick={() => setActiveSourceTab('ITC_IN_BOOKS')}
                                className={`erp-tab whitespace-nowrap ${activeSourceTab === 'ITC_IN_BOOKS' ? 'active' : ''}`}
                            >
                                ITC IN BOOKS
                            </button>
                            <button
                                onClick={() => setActiveSourceTab('GSTR2B')}
                                className={`erp-tab whitespace-nowrap ${activeSourceTab === 'GSTR2B' ? 'active' : ''}`}
                            >
                                GSTR-2B
                            </button>
                        </div>
                        <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider pr-2 select-none hidden sm:inline">
                            {activeSourceTab === 'ITC_IN_BOOKS' ? 'Source: Books Inward Supplies' : 'Source: Government GSTR-2B'}
                        </span>
                    </div>
                </div>

                {/* ── ITC IN BOOKS: Period Controls & Sub-tabs ── */}
                {activeSourceTab === 'ITC_IN_BOOKS' && (
                    <>
                        {renderPeriodControls(fetchData, isLoading)}
                        <div className="erp-container p-0 shadow-sm overflow-hidden">
                            <div
                                className="erp-tab-container mb-0 border-b border-slate-100 px-6 overflow-x-auto overflow-y-hidden select-none"
                                onWheel={(e) => {
                                    if (e.deltaY !== 0) {
                                        e.currentTarget.scrollLeft += e.deltaY;
                                    }
                                }}
                            >
                                {subTabs.map((tab) => (
                                    <button
                                        key={tab}
                                        ref={activeSubTab === tab ? activeTabRef : null}
                                        onClick={() => setActiveSubTab(tab)}
                                        className={`erp-tab whitespace-nowrap ${activeSubTab === tab ? 'active' : ''}`}
                                    >
                                        {tab} {stats[tab] !== undefined && stats[tab] > 0 ? `(${stats[tab]})` : ''}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </>
                )}

                {/* ── GSTR-2B: Period Controls & Sub-tabs ── */}
                {activeSourceTab === 'GSTR2B' && (
                    <>
                        {renderPeriodControls(fetchGstr2bData, gstr2bLoading)}
                        <div className="erp-container p-0 shadow-sm overflow-hidden">
                            <div
                                className="erp-tab-container mb-0 border-b border-slate-100 px-6 overflow-x-auto overflow-y-hidden select-none"
                                onWheel={(e) => {
                                    if (e.deltaY !== 0) {
                                        e.currentTarget.scrollLeft += e.deltaY;
                                    }
                                }}
                            >
                                {subTabs.map((tab) => (
                                    <button
                                        key={tab}
                                        ref={activeSubTab === tab ? activeTabRef : null}
                                        onClick={() => setActiveSubTab(tab)}
                                        className={`erp-tab whitespace-nowrap ${activeSubTab === tab ? 'active' : ''}`}
                                    >
                                        {tab} {tab === 'B2B' && gstr2bInvoices.length > 0 ? `(${gstr2bInvoices.length})` : ''}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* ITC IN BOOKS Content (Accounting Books Inward Data)             */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            {activeSourceTab === 'ITC_IN_BOOKS' && (
                <div className="erp-container p-0">
                    <div className="p-6 overflow-x-auto w-full max-w-full block">
                        {isLoading && (
                            <div className="flex justify-center py-8">
                                <div className="animate-spin rounded-[4px] h-8 w-8 border-b-2 border-indigo-600"></div>
                            </div>
                        )}

                        {!isLoading && activeSubTab === 'B2B' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">B2B Invoices - Business to Registered Business (Purchases)</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {b2bData.length > 0 ? b2bData.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(row, 'Purchase')}>
                                                    <td className="px-4 py-2 border text-sm">{row.gstin}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={10} className="px-4 py-8 text-center text-gray-500">No B2B purchases found in Books.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!isLoading && activeSubTab === 'B2BUR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">B2BUR - Purchases from Unregistered Vendors</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {b2burData.length > 0 ? b2burData.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(row, 'Purchase')}>
                                                    <td className="px-4 py-2 border text-sm">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={9} className="px-4 py-8 text-center text-gray-500">No B2BUR purchases found in Books.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!isLoading && activeSubTab === 'IMPG' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">IMPG - Import of Goods</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Port Code</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {impgData.length > 0 ? impgData.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(row, 'Purchase')}>
                                                    <td className="px-4 py-2 border text-sm">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.port_code}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.boe_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.boe_date}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.boe_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No IMPG records found in Books.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!isLoading && activeSubTab === 'CDNR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">CDNR - Credit/Debit Notes (Registered)</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Type</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {cdnrData.length > 0 ? cdnrData.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(row, 'Debit Note')}>
                                                    <td className="px-4 py-2 border text-sm">{row.gstin}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_date}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_type}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={11} className="px-4 py-8 text-center text-gray-500">No CDNR records found in Books.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!isLoading && activeSubTab === 'CDNUR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">CDNUR - Credit/Debit Notes (Unregistered)</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Type</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {cdnurData.length > 0 ? cdnurData.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(row, 'Debit Note')}>
                                                    <td className="px-4 py-2 border text-sm">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_date}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.note_type}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={10} className="px-4 py-8 text-center text-gray-500">No CDNUR records found in Books.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* GSTR-2B Content (Government Invoices from GSTR2BInvoice model)  */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            {activeSourceTab === 'GSTR2B' && (
                <div className="erp-container p-0">
                    <div className="p-6 overflow-x-auto w-full max-w-full block">
                        {gstr2bLoading && (
                            <div className="flex justify-center py-8">
                                <div className="animate-spin rounded-[4px] h-8 w-8 border-b-2 border-indigo-600"></div>
                            </div>
                        )}

                        {!gstr2bLoading && activeSubTab === 'B2B' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">
                                    B2B Invoices - Business to Registered Business (Purchases)
                                    {gstr2bTotal > 0 && (
                                        <span className="ml-2 text-xs font-normal text-slate-500 normal-case">
                                            ({gstr2bTotal} invoice{gstr2bTotal !== 1 ? 's' : ''} in GSTR-2B for {period.month} {period.year})
                                        </span>
                                    )}
                                </h3>

                                {gstr2bInvoices.length === 0 ? (
                                    <div className="text-center py-12">
                                        <div className="mx-auto w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4 text-3xl">🏛</div>
                                        <p className="text-slate-600 font-medium">No GSTR-2B purchases found.</p>
                                        <p className="text-slate-400 text-sm mt-1">
                                            Upload your government GSTR-2B JSON file via the{' '}
                                            <span className="font-semibold text-indigo-600">GSTR-2B Reconciliation</span> module to view government data here.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="erp-table-container">
                                        <table className="erp-table">
                                            <thead>
                                                <tr>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                    <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {gstr2bInvoices.map((row, idx) => (
                                                    <tr key={row.id || idx} className="hover:bg-gray-50">
                                                        <td className="px-4 py-2 border text-sm font-mono">{row.gstin}</td>
                                                        <td className="px-4 py-2 border text-sm">{row.supplier_name || '—'}</td>
                                                        <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                        <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                        <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                        <td className="px-4 py-2 border text-sm">{row.place_of_supply || '—'}</td>
                                                        <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                        <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                        <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                        <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        )}

                        {!gstr2bLoading && activeSubTab === 'B2BUR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">B2BUR - Purchases from Unregistered Vendors</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">No B2BUR purchases found in GSTR-2B.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!gstr2bLoading && activeSubTab === 'IMPG' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">IMPG - Import of Goods</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Port Code</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">BOE Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No IMPG records found in GSTR-2B.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!gstr2bLoading && activeSubTab === 'CDNR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">CDNR - Credit/Debit Notes (Registered)</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Type</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">No CDNR records found in GSTR-2B.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {!gstr2bLoading && activeSubTab === 'CDNUR' && (
                            <div>
                                <h3 className="erp-section-title border-none pb-0 mb-4">CDNUR - Credit/Debit Notes (Unregistered)</h3>
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Type</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Note Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colSpan={10} className="px-4 py-8 text-center text-gray-500">No CDNUR records found in GSTR-2B.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}


