import React, { useState, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';
import { apiService } from '../../services/api';

let savedPeriod: { year: string; month: string } | null = null;
let savedSubTab: string = 'B2B';

export default function GSTR1Page({ onNavigate, setViewVoucherData, vouchers }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void, vouchers?: any[] }) {
    const [activeSubTab, setActiveSubTabState] = useState(savedSubTab);
    const setActiveSubTab = (tab: string) => { savedSubTab = tab; setActiveSubTabState(tab); };
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
const [activeGstin, setActiveGstin] = useState<string>('');
    const [b2baData, setB2baData] = useState<any[]>([]);
    const [isFilingReturn, setIsFilingReturn] = useState(false);
    const [filingStatus, setFilingStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showAmendmentModal, setShowAmendmentModal] = useState(false);
    const [viewAmendmentData, setViewAmendmentData] = useState<any>(null);
    const [selectedB2csRow, setSelectedB2csRow] = useState<any>(null);
    const [selectedExempRow, setSelectedExempRow] = useState<any>(null);
    const [selectedEcoRow, setSelectedEcoRow] = useState<any>(null);
    const [amendmentForm, setAmendmentForm] = useState<any>({});
    const [selectedInvoice, setSelectedInvoice] = useState<any>(null);

    // HSN Drilldown State
    const [showHsnDrilldown, setShowHsnDrilldown] = useState(false);
    const [hsnDrilldownData, setHsnDrilldownData] = useState<any[]>([]);
    const [hsnDrilldownLoading, setHsnDrilldownLoading] = useState(false);
    const [currentHsnParams, setCurrentHsnParams] = useState<any>(null);

    // DOC Drilldown State
    const [showDocDrilldown, setShowDocDrilldown] = useState(false);
    const [docDrilldownData, setDocDrilldownData] = useState<any[]>([]);
    const [docDrilldownLoading, setDocDrilldownLoading] = useState(false);

    // OTP State — shared for both normal filing and amendment filing
    const [showOtpModal, setShowOtpModal] = useState(false);
    const [isAmendmentMode, setIsAmendmentMode] = useState(false); // true = filing amendment
    const [otpValue, setOtpValue] = useState('');
    const [isSendingOtp, setIsSendingOtp] = useState(false);
    const [otpSent, setOtpSent] = useState(false);
    const [isFilingAmendment, setIsFilingAmendment] = useState(false);
    const [amendmentFilingStatus, setAmendmentFilingStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    // Data states
    const [b2bData, setB2bData] = useState<any[]>([]);
    const [b2clData, setB2clData] = useState<any[]>([]);
    const [b2claData, setB2claData] = useState<any[]>([]);
    const [b2csData, setB2csData] = useState<any[]>([]);
    const [b2csaData, setB2csaData] = useState<any[]>([]);
    const [cdnrData, setCdnrData] = useState<any[]>([]);
    const [cdnraData, setCdnraData] = useState<any[]>([]);
    const [cdnurData, setCdnurData] = useState<any[]>([]);
    const [cdnuraData, setCdnuraData] = useState<any[]>([]);
    const [atData, setAtData] = useState<any[]>([]);
    const [ataData, setAtaData] = useState<any[]>([]);
    const [atadjData, setAtadjData] = useState<any[]>([]);
    const [atadjaData, setAtadjaData] = useState<any[]>([]);
    const [exempData, setExempData] = useState<any[]>([]);
    const [docData, setDocData] = useState<any[]>([]);
    const [expData, setExpData] = useState<any[]>([]);
    const [expaData, setExpaData] = useState<any[]>([]);
    const [ecoData, setEcoData] = useState<any[]>([]);
    const [ecoaData, setEcoaData] = useState<any[]>([]);
    const [ecob2bData, setEcob2bData] = useState<any[]>([]);
    const [ecob2cData, setEcob2cData] = useState<any[]>([]);
    const [ecoab2bData, setEcoab2bData] = useState<any[]>([]);
    const [ecoab2cData, setEcoab2cData] = useState<any[]>([]);
    const [ecourp2bData, setEcourp2bData] = useState<any[]>([]);
    const [ecourp2cData, setEcourp2cData] = useState<any[]>([]);
    const [ecoaurp2bData, setEcoaurp2bData] = useState<any[]>([]);
    const [ecoaurp2cData, setEcoaurp2cData] = useState<any[]>([]);
    const [hsnData, setHsnData] = useState<any[]>([]);
    const [hsnB2bData, setHsnB2bData] = useState<any[]>([]);
    const [hsnB2cData, setHsnB2cData] = useState<any[]>([]);
    const [stats, setStats] = useState<Record<string, number>>({});

useEffect(() => {
    apiService.getCompanyDetails().then(res => {
        if (res && res.gstin) {
            setActiveGstin(res.gstin);
        }
    }).catch(err => console.error('Failed to fetch active GSTIN', err));
}, []);

    const subTabs = [
        // Original tabs
        'B2B', 'B2BA', 'B2CL', 'B2CLA', 'B2CS', 'B2CSA',
        'CDNR', 'CDNRA', 'CDNUR', 'CDNURA',
        'EXP', 'EXPA',
        'AT', 'ATA', 'ATADJ', 'ATADJA',
        // E-commerce tabs
        'ECO', 'ECOA', 'ECOB2B', 'ECOURP2B', 'ECOB2C', 'ECOURP2C',
        'ECOAB2B', 'ECOAB2C', 'ECOAURP2B', 'ECOAURP2C',
        // Other tabs
        'EXEMP', 'HSNB2B', 'HSNB2C', 'DOC'
    ];

    useEffect(() => {
        const saved = localStorage.getItem('gstr1_b2ba_data');
        if (saved) {
            try {
                setB2baData(JSON.parse(saved));
            } catch (e) { }
        }
    }, []);

    useEffect(() => {
        if (b2baData.length > 0) {
            localStorage.setItem('gstr1_b2ba_data', JSON.stringify(b2baData));
        }
    }, [b2baData]);

    useEffect(() => {
        // B2BA now comes from backend which already excludes amended from B2B
        // No manual frontend filtering needed
    }, []);


    const fetchData = async () => {
        setIsLoading(true);
        try {
            // Fetch stats first
            let queryParams = new URLSearchParams(period as any).toString();
            const statsRes = await httpClient.get<Record<string, number>>(`/api/gst/gstr1/stats/?${queryParams}`);
            setStats(statsRes || {});

            // Mapping tab names to API endpoints
            const endpointMap: Record<string, string> = {
                'B2B': '/api/gst/gstr1/b2b/',
                'B2BA': '/api/gst/gstr1/b2ba/',
                'B2CL': '/api/gst/gstr1/b2cl/',
                'B2CLA': '/api/gst/gstr1/b2cla/',
                'B2CS': '/api/gst/gstr1/b2cs/',
                'B2CSA': '/api/gst/gstr1/b2csa/',
                'CDNR': '/api/gst/gstr1/cdnr/',
                'CDNRA': '/api/gst/gstr1/cdnra/',
                'CDNUR': '/api/gst/gstr1/cdnur/',
                'CDNURA': '/api/gst/gstr1/cdnura/',
                'EXP': '/api/gst/gstr1/exp/',
                'EXPA': '/api/gst/gstr1/expa/',
                'AT': '/api/gst/gstr1/at/',
                'ATA': '/api/gst/gstr1/ata/',
                'ATADJ': '/api/gst/gstr1/atadj/',
                'ATADJA': '/api/gst/gstr1/atadja/',
                'EXEMP': '/api/gst/gstr1/exemp/',
                'DOC': '/api/gst/gstr1/doc/',
                'HSNB2B': '/api/gst/gstr1/hsnb2b/',
                'HSNB2C': '/api/gst/gstr1/hsnb2c/',
                'ECO': '/api/gst/gstr1/eco/',
                'ECOA': '/api/gst/gstr1/ecoa/',
                'ECOB2B': '/api/gst/gstr1/ecob2b/',
                'ECOB2C': '/api/gst/gstr1/ecob2c/',
                'ECOAB2B': '/api/gst/gstr1/ecoab2b/',
                'ECOAB2C': '/api/gst/gstr1/ecoab2c/',
                'ECOURP2B': '/api/gst/gstr1/ecourp2b/',
                'ECOURP2C': '/api/gst/gstr1/ecourp2c/',
                'ECOAURP2B': '/api/gst/gstr1/ecoaurp2b/',
                'ECOAURP2C': '/api/gst/gstr1/ecoaurp2c/',
            };

            const url = endpointMap[activeSubTab];
            if (!url) {
                setIsLoading(false);
                // Clear data for tabs that don't have an endpoint
                switch (activeSubTab) {
                    case 'B2B': setB2bData([]); break;
                    case 'B2BA': setB2baData([]); break;
                    case 'B2CL': setB2clData([]); break;
                    case 'B2CLA': setB2claData([]); break;
                    case 'B2CS': setB2csData([]); break;
                    case 'B2CSA': setB2csaData([]); break;
                    case 'CDNR': setCdnrData([]); break;
                    case 'CDNRA': setCdnraData([]); break;
                    case 'CDNUR': setCdnurData([]); break;
                    case 'CDNURA': setCdnuraData([]); break;
                    case 'AT': setAtData([]); break;
                    case 'ATA': setAtaData([]); break;
                    case 'ATADJ': setAtadjData([]); break;
                    case 'EXEMP': setExempData([]); break;
                    case 'DOC': setDocData([]); break;
                    case 'EXP': setExpData([]); break;
                    case 'HSN': setHsnData([]); break;
                    case 'HSNB2B': setHsnB2bData([]); break;
                    case 'HSNB2C': setHsnB2cData([]); break;
                    case 'ECO': setEcoData([]); break;
                    case 'ECOA': setEcoaData([]); break;
                    case 'ECOB2B': setEcob2bData([]); break;
                    case 'ECOB2C': setEcob2cData([]); break;
                    case 'ECOAB2B': setEcoab2bData([]); break;
                    case 'ECOAB2C': setEcoab2cData([]); break;
                    case 'ECOURP2B': setEcourp2bData([]); break;
                    case 'ECOURP2C': setEcourp2cData([]); break;
                    case 'ECOAURP2B': setEcoaurp2bData([]); break;
                    case 'ECOAURP2C': setEcoaurp2cData([]); break;
                }
                return;
            }

            // In a real application, you'd pass period as query parameters
            queryParams = new URLSearchParams(period as any).toString();
            const fullUrl = `${url}?${queryParams}`;
            const response = await httpClient.get<any[]>(fullUrl);
            console.log(`[CDNR DEBUG] fetched URL=${fullUrl}`, response);

            switch (activeSubTab) {
                case 'B2B':
                    setB2bData(response || []);
                    break;
                case 'B2BA': setB2baData(response || []); break;
                case 'B2CL': setB2clData(response || []); break;
                case 'B2CLA': setB2claData(response || []); break;
                case 'B2CS': setB2csData(response || []); break;
                case 'B2CSA': setB2csaData(response || []); break;
                case 'CDNR': setCdnrData(response || []); break;
                case 'CDNRA': setCdnraData(response || []); break;
                case 'CDNUR': setCdnurData(response || []); break;
                case 'CDNURA': setCdnuraData(response || []); break;
                case 'AT': setAtData(response || []); break;
                case 'ATA': setAtaData(response || []); break;
                case 'ATADJ': setAtadjData(response || []); break;
                case 'ATADJA': setAtadjaData(response || []); break;
                case 'EXEMP': setExempData(response || []); break;
                case 'DOC': setDocData(response || []); break;
                case 'EXP': setExpData(response || []); break;
                case 'EXPA': setExpaData(response || []); break;
                case 'HSN': setHsnData(response || []); break;
                case 'HSNB2B': setHsnB2bData(response || []); break;
                case 'HSNB2C': setHsnB2cData(response || []); break;
                case 'ECO': setEcoData(response || []); break;
                case 'ECOA': setEcoaData(response || []); break;
                case 'ECOB2B': setEcob2bData(response || []); break;
                case 'ECOB2C': setEcob2cData(response || []); break;
                case 'ECOAB2B': setEcoab2bData(response || []); break;
                case 'ECOAB2C': setEcoab2cData(response || []); break;
                case 'ECOURP2B': setEcourp2bData(response || []); break;
                case 'ECOURP2C': setEcourp2cData(response || []); break;
                case 'ECOAURP2B': setEcoaurp2bData(response || []); break;
                case 'ECOAURP2C': setEcoaurp2cData(response || []); break;
                default:
                    // Clear data for other tabs if they were previously populated
                    setB2bData([]);
                    setB2clData([]);
                    setB2csData([]);
                    setCdnrData([]);
                    setCdnurData([]);
                    setAtData([]);
                    setAtaData([]);
                    setAtadjData([]);
                    setAtadjaData([]);
                    setExempData([]);
                    setDocData([]);
                    setExpData([]);
                    setHsnData([]);
                    setHsnB2bData([]);
                    setHsnB2cData([]);
                    break;
            }
        } catch (error) {
            console.error('Failed to fetch GSTR1 data:');
            // Clear data on error
            switch (activeSubTab) {
                case 'B2B': setB2bData([]); break;
                case 'B2CL': setB2clData([]); break;
                case 'B2CLA': setB2claData([]); break;
                case 'B2CS': setB2csData([]); break;
                case 'B2CSA': setB2csaData([]); break;
                case 'CDNR': setCdnrData([]); break;
                case 'CDNRA': setCdnraData([]); break;
                case 'CDNUR': setCdnurData([]); break;
                case 'CDNURA': setCdnuraData([]); break;
                case 'AT': setAtData([]); break;
                case 'ATA': setAtaData([]); break;
                case 'ATADJ': setAtadjData([]); break;
                case 'ATADJA': setAtadjaData([]); break;
                case 'EXEMP': setExempData([]); break;
                case 'DOC': setDocData([]); break;
                case 'EXP': setExpData([]); break;
                case 'HSN': setHsnData([]); break;
                case 'HSNB2B': setHsnB2bData([]); break;
                case 'HSNB2C': setHsnB2cData([]); break;
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleDownloadExcel = async () => {
        try {
            const queryParams = new URLSearchParams(period as any).toString();
            const response: any = await httpClient.get(`/api/gst/gstr1/download_excel/?${queryParams}`);

            const url = window.URL.createObjectURL(response);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `GSTR1_${period.year}_${period.month}.xlsx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Download failed');
        }
    };

    const handleDownloadJson = async () => {
        try {
            const queryParams = new URLSearchParams(period as any).toString();
            const response: any = await httpClient.get(`/api/gst/gstr1/download_json/?${queryParams}`);

            const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `GSTR1_${period.year}_${period.month}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Download JSON failed');
        }
    };

    const handleHsnRowClick = async (row: any, isB2b: boolean) => {
        setCurrentHsnParams({ hsn: row.hsn, rate: row.rate, isB2b });
        setShowHsnDrilldown(true);
        setHsnDrilldownLoading(true);
        try {
            const queryParams = new URLSearchParams({
                ...(period as any),
                hsn_code: row.hsn,
                rate: row.rate,
                is_b2b: isB2b.toString()
            }).toString();
            const response = await httpClient.get<any[]>(`/api/gst/gstr1/hsn_invoices/?${queryParams}`);
            setHsnDrilldownData(response || []);
        } catch (e) {
            setHsnDrilldownData([]);
        } finally {
            setHsnDrilldownLoading(false);
        }
    };

    const handleDocRowClick = async () => {
        setShowDocDrilldown(true);
        setDocDrilldownLoading(true);
        try {
            const queryParams = new URLSearchParams(period as any).toString();
            const response = await httpClient.get<any[]>(`/api/gst/gstr1/doc_details/?${queryParams}`);
            setDocDrilldownData(response || []);
        } catch (e) {
            setDocDrilldownData([]);
        } finally {
            setDocDrilldownLoading(false);
        }
    };

    // Check if selected period is the current or future month (filing not allowed)
    const isCurrentOrFutureMonth = (() => {
        const today = new Date();
        const currentYear = today.getFullYear();
        const currentMonth = today.getMonth() + 1; // 1-indexed
        const fyStartYear = parseInt(period.year.split('-')[0]);
        const monthsMap: Record<string, { num: number; offset: number }> = {
            'April': { num: 4, offset: 0 }, 'May': { num: 5, offset: 0 }, 'June': { num: 6, offset: 0 },
            'July': { num: 7, offset: 0 }, 'August': { num: 8, offset: 0 }, 'September': { num: 9, offset: 0 },
            'October': { num: 10, offset: 0 }, 'November': { num: 11, offset: 0 }, 'December': { num: 12, offset: 0 },
            'January': { num: 1, offset: 1 }, 'February': { num: 2, offset: 1 }, 'March': { num: 3, offset: 1 }
        };
        const info = monthsMap[period.month];
        if (!info) return false;
        const filterYear = fyStartYear + info.offset;
        
        if (filterYear > currentYear) return true;
        if (filterYear === currentYear && info.num >= currentMonth) return true;
        return false;
    })();

    const initiateFiling = () => {
        setFilingStatus(null);
        setIsAmendmentMode(false);
        setShowOtpModal(true);
        setOtpSent(false);
        setOtpValue('');
    };

    const initiateAmendmentFiling = () => {
        setAmendmentFilingStatus(null);
        setFilingStatus(null);
        setIsAmendmentMode(true);
        setShowOtpModal(true);
        setOtpSent(false);
        setOtpValue('');
    };

    const handleRequestOTP = async () => {
        setIsSendingOtp(true);
        setFilingStatus(null);
        try {
            const res = await apiService.requestSandboxOTP(activeGstin || '29AAACQ3770E000');
            setFilingStatus({ type: 'success', message: res?.message || 'OTP Sent successfully' });
            setOtpSent(true);
        } catch (err: any) {
            const msg = err?.response?.data?.error || err?.message || 'Failed to request OTP.';
            setFilingStatus({ type: 'error', message: msg });
        } finally {
            setIsSendingOtp(false);
        }
    };

    const handleVerifyAndFile = async () => {
        if (!otpValue) {
            setFilingStatus({ type: 'error', message: 'Please enter the OTP' });
            return;
        }

        if (isAmendmentMode) {
            // --- File Amendment ---
            setIsFilingAmendment(true);
            setAmendmentFilingStatus(null);
            try {
                const res = await httpClient.post<any>('/api/gst/gstr1/file_amendment/', {
                    year: period.year,
                    month: period.month,
                    otp: otpValue,
                });
                setAmendmentFilingStatus({
                    type: 'success',
                    message: res?.message || `Amendment filed successfully for ${period.month} ${period.year}.`
                });
                setShowOtpModal(false);
                fetchData(); // refresh tabs — EXPA/B2BA counts drop to 0
            } catch (err: any) {
                const msg = err?.response?.data?.error || err?.message || 'Failed to file amendment.';
                setAmendmentFilingStatus({ type: 'error', message: msg });
            } finally {
                setIsFilingAmendment(false);
            }
        } else {
            // --- Normal GST Return Filing ---
            setIsFilingReturn(true);
            setFilingStatus(null);
            try {
                const res = await apiService.verifyAndFileSandbox(period.month, period.year, { b2b: b2bData }, otpValue, activeGstin);
                setFilingStatus({
                    type: 'success',
                    message: res?.message || `GST Return filed successfully for ${period.month} ${period.year}.`
                });
                setShowOtpModal(false);
                fetchData();
            } catch (err: any) {
                const msg = err?.response?.data?.error || err?.message || 'Failed to file GST return.';
                setFilingStatus({ type: 'error', message: msg });
            } finally {
                setIsFilingReturn(false);
            }
        }
    };


    useEffect(() => {
        fetchData();
    }, [activeSubTab, period]); // Refetch on tab or period change

    return (
        <div className="space-y-6">
            {/* Period Selector */}
            <div className="erp-container">
                <div className="flex flex-wrap items-end gap-6">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Financial Year</label>
                        <select
                            value={period.year}
                            onChange={(e) => setPeriod({ ...period, year: e.target.value })}
                            className="erp-select"
                        >
                            {/* ... years ... */}
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
                    <div className="flex-1 min-w-[200px]">
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
                            onClick={fetchData}
                            className="erp-button-primary"
                            disabled={isLoading}
                        >
                            {isLoading ? 'Generating...' : 'Generate Return'}
                        </button>
                        {!(activeSubTab === 'EXPA' || activeSubTab === 'B2BA' || activeSubTab === 'B2CLA' || activeSubTab === 'B2CSA' || activeSubTab === 'ATADJA' || activeSubTab === 'ATA' || activeSubTab.startsWith('ECOA') || activeSubTab === 'CDNRA' || activeSubTab === 'CDNURA') && (
                            <button
                                onClick={initiateFiling}
                                disabled={isFilingReturn || isLoading || isCurrentOrFutureMonth}
                                title={isCurrentOrFutureMonth ? "Cannot file for current or future months" : "File directly to Sandbox API"}
                                className={`erp-button-primary ${isCurrentOrFutureMonth ? 'bg-gray-400 border-gray-400 hover:bg-gray-400 cursor-not-allowed opacity-70' : 'bg-emerald-600 hover:bg-emerald-700 border-emerald-600'}`}
                            >
                                ⚡ File GST Return (Sandbox)
                            </button>
                        )}
                        {/* Amendment Filing Button — visible on ALL amendment tabs */}
                        {(activeSubTab === 'EXPA' || activeSubTab === 'B2BA' || activeSubTab === 'B2CLA' || activeSubTab === 'B2CSA' || activeSubTab === 'ATADJA' || activeSubTab === 'ATA' || activeSubTab.startsWith('ECOA') || activeSubTab === 'CDNRA' || activeSubTab === 'CDNURA') && (
                            <button
                                onClick={initiateAmendmentFiling}
                                disabled={isFilingAmendment || isLoading || isCurrentOrFutureMonth}
                                title={isCurrentOrFutureMonth ? "Cannot file for current or future months" : `File all pending ${activeSubTab} amendments to GST portal`}
                                className={`erp-button-primary flex items-center gap-2 ${
                                    isCurrentOrFutureMonth
                                        ? 'bg-gray-400 border-gray-400 hover:bg-gray-400 cursor-not-allowed opacity-70'
                                        : 'bg-amber-600 hover:bg-amber-700 border-amber-600'
                                }`}
                            >
                                📝 File Amendment ({activeSubTab})
                            </button>
                        )}
                        {/* Amendment Status Banner (inline) */}
                        {amendmentFilingStatus && (
                            <span className={`text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1 ${
                                amendmentFilingStatus.type === 'success'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : 'bg-red-50 text-red-700 border border-red-200'
                            }`}>
                                {amendmentFilingStatus.type === 'success' ? '✅' : '❌'} {amendmentFilingStatus.message}
                            </span>
                        )}
                        <button
                            onClick={handleDownloadExcel}
                            className="erp-button-secondary"
                            disabled={isLoading}
                        >
                            Download Excel
                        </button>
                        <button
                            onClick={handleDownloadJson}
                            className="erp-button-secondary bg-amber-50 text-amber-700 border-amber-100 hover:bg-amber-100"
                            disabled={isLoading}
                        >
                            Download JSON
                        </button>
                    </div>
                </div>
                {/* Filing Status Banner */}
                {filingStatus && (
                    <div className={`mt-4 px-4 py-3 rounded-xl text-sm font-medium flex items-center justify-between gap-4 ${filingStatus.type === 'success'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-red-50 text-red-800 border border-red-200'
                        }`}>
                        <span>{filingStatus.type === 'success' ? '✅' : '❌'} {filingStatus.message}</span>
                        <button onClick={() => setFilingStatus(null)} className="text-xs opacity-60 hover:opacity-100">✕</button>
                    </div>
                )}
            </div>

            {/* Sub Tabs */}
            <div className="erp-container p-0">
                <div className="erp-tab-container mb-0 border-b border-slate-100 px-6 overflow-x-auto">
                    {subTabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveSubTab(tab)}
                            className={`erp-tab ${activeSubTab === tab ? 'active' : ''}`}
                        >
                            {tab} {stats[tab] !== undefined && stats[tab] > 0 ? `(${stats[tab]})` : ''}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="p-6">
                    {/* Loading State */}
                    {isLoading && (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-[4px] h-8 w-8 border-b-2 border-indigo-600"></div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2B Invoices - Business to Registered Business</h3>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Recipient Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rev. Charge</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2bData.length > 0 ? b2bData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className={`hover:bg-gray-50 cursor-pointer`}
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.invoice_no,
                                                            type: 'Sales',
                                                            source: 'b2b_drilldown'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.gstin}</td>
                                                <td className="px-4 py-2 border text-sm">{row.recipient_name}</td>
                                                <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.reverse_charge}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                                                    No B2B invoices found for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2BA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2BA - B2B Invoices (Amendment)</h3>
                            <p className="text-sm text-gray-600 mb-4">Shows original GST Filed values.</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Recipient*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Name of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Reverse Charge*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Amendment Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2baData.length > 0 ? b2baData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className={`hover:bg-blue-50 cursor-pointer`}
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.original_invoice_no,
                                                            type: 'Sales',
                                                            source: 'b2b_drilldown',
                                                            _viewAsGSTFiled: true 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.gstin || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.recipient_name || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.reverse_charge || 'N'}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.igst || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm" onClick={(e) => e.stopPropagation()}>
                                                    {row.amendment_filed ? (
                                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            ✅ Filed
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            Pending
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                                                    No B2BA data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CL' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2C Large - Invoices above ₹2.5 Lakhs</h3>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2clData.length > 0 ? b2clData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-gray-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.invoice_no,
                                                            type: 'Sales',
                                                            source: 'b2cl_drilldown'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                                                    No B2C Large invoices found.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CLA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2CLA - B2C Large (Amendment)</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended details of B2C Large invoices (original GST filed vs revised values)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Invoice No.</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Invoice Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Invoice No.</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Invoice Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original POS</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised POS</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2claData.length > 0 ? b2claData.map((row, idx) => (
                                            <tr
                                                key={idx}
                                                className="hover:bg-amber-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.revised_invoice_no,
                                                            type: 'Sales',
                                                            source: 'b2cla_drilldown',
                                                            _viewAsGSTFiled: true
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm font-medium text-gray-500">{row.original_invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm text-gray-500">{row.original_invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm font-medium text-blue-700">{row.revised_invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.revised_invoice_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.revised_igst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                                    No B2CLA amendments for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CS' && (
                        <div>
                            {selectedB2csRow ? (
                                <div>
                                    <div className="flex items-center mb-6 border-b pb-4">
                                        <button 
                                            onClick={() => setSelectedB2csRow(null)}
                                            className="mr-4 px-4 py-2 text-sm font-semibold text-indigo-600 bg-indigo-50 rounded-xl hover:bg-indigo-100 transition-colors flex items-center gap-2"
                                        >
                                            <span className="text-lg leading-none">&larr;</span> Back to Summary
                                        </button>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-800 border-none pb-0 mb-0">
                                                Invoices for Place of Supply: {selectedB2csRow.place_of_supply || selectedB2csRow.revised_pos}
                                            </h3>
                                            <p className="text-sm text-gray-500 mt-1">
                                                Click on an invoice to view or amend it.
                                            </p>
                                        </div>
                                    </div>
                                    <div className="erp-table-container">
                                        <table className="erp-table w-full">
                                            <thead>
                                                <tr>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Invoice No</th>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Date</th>
                                                    <th className="px-4 py-3 border-b text-right text-sm font-semibold text-gray-600">Value</th>
                                                    <th className="px-4 py-3 border-b text-center text-sm font-semibold text-gray-600">Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(selectedB2csRow.vouchers || []).map((v: any) => (
                                                    <tr
                                                        key={v.id}
                                                        className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                                        onClick={() => {
                                                            setSelectedB2csRow(null);
                                                            if (setViewVoucherData && onNavigate) {
                                                                setViewVoucherData({
                                                                    ...v,
                                                                    voucherNo: v.invoice_no,
                                                                    type: 'Sales',
                                                                    source: 'b2cs_drilldown',
                                                                    _viewAsGSTFiled: v.amendment_date ? true : false
                                                                });
                                                                onNavigate('Vouchers');
                                                            }
                                                        }}
                                                    >
                                                        <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.invoice_no}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-600">{v.invoice_date}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-800 text-right font-medium">?{Number(v.invoice_value).toFixed(2)}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-center">
                                                            {v.amendment_date ? (
                                                                <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase">Amended</span>
                                                            ) : v.gst_registered === 'Yes' ? (
                                                                <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase">GST Filed</span>
                                                            ) : (
                                                                <span className="px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-[10px] font-bold uppercase">Pending</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                                {(!selectedB2csRow.vouchers || selectedB2csRow.vouchers.length === 0) && (
                                                    <tr>
                                                        <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                            No detailed invoices found.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <h3 className="erp-section-title border-none pb-0 mb-4">B2C Small - Summary of Small Invoices</h3>
                            <p className="text-sm text-gray-600 mb-4">Aggregated summary by Place of Supply and Tax Rate</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Type</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2csData.length > 0 ? b2csData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedB2csRow(row)}>
                                                <td className="px-4 py-2 border text-sm">{row.type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.igst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cgst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.sgst).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                                                    No B2C Small data available.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CSA' && (
                        <div>
                            {selectedB2csRow ? (
                                <div>
                                    <div className="flex items-center mb-6 border-b pb-4">
                                        <button 
                                            onClick={() => setSelectedB2csRow(null)}
                                            className="mr-4 px-4 py-2 text-sm font-semibold text-indigo-600 bg-indigo-50 rounded-xl hover:bg-indigo-100 transition-colors flex items-center gap-2"
                                        >
                                            <span className="text-lg leading-none">&larr;</span> Back to Summary
                                        </button>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-800 border-none pb-0 mb-0">
                                                Invoices for Place of Supply: {selectedB2csRow.place_of_supply || selectedB2csRow.revised_pos}
                                            </h3>
                                            <p className="text-sm text-gray-500 mt-1">
                                                Click on an invoice to view or amend it.
                                            </p>
                                        </div>
                                    </div>
                                    <div className="erp-table-container">
                                        <table className="erp-table w-full">
                                            <thead>
                                                <tr>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Invoice No</th>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Date</th>
                                                    <th className="px-4 py-3 border-b text-right text-sm font-semibold text-gray-600">Value</th>
                                                    <th className="px-4 py-3 border-b text-center text-sm font-semibold text-gray-600">Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(selectedB2csRow.vouchers || []).map((v: any) => (
                                                    <tr
                                                        key={v.id}
                                                        className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                                        onClick={() => {
                                                            setSelectedB2csRow(null);
                                                            if (setViewVoucherData && onNavigate) {
                                                                setViewVoucherData({
                                                                    ...v,
                                                                    voucherNo: v.invoice_no,
                                                                    type: 'Sales',
                                                                    source: 'b2cs_drilldown',
                                                                    _viewAsGSTFiled: v.amendment_date ? true : false
                                                                });
                                                                onNavigate('Vouchers');
                                                            }
                                                        }}
                                                    >
                                                        <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.invoice_no}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-600">{v.invoice_date}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-800 text-right font-medium">?{Number(v.invoice_value).toFixed(2)}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-center">
                                                            {v.amendment_date ? (
                                                                <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase">Amended</span>
                                                            ) : v.gst_registered === 'Yes' ? (
                                                                <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase">GST Filed</span>
                                                            ) : (
                                                                <span className="px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-[10px] font-bold uppercase">Pending</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                                {(!selectedB2csRow.vouchers || selectedB2csRow.vouchers.length === 0) && (
                                                    <tr>
                                                        <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                            No detailed invoices found.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <h3 className="erp-section-title border-none pb-0 mb-4">B2CSA - B2C Small (Amendment)</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended details of B2C Small supplies</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Financial Year</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Month</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Place of Supply(POS)</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Place of Supply(POS)</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">E-Commerce GSTIN</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Amendment Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {b2csaData.length > 0 ? b2csaData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedB2csRow(row)}>
                                                <td className="px-4 py-2 border text-sm">{row.type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.financial_year}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_month}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_pos}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_pos}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.ecommerce_gstin || '-'}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                                                    No B2CSA data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'CDNR' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">CDNR - Credit/Debit Notes (Registered)</h3>
                            <p className="text-sm text-gray-600 mb-4">Credit and Debit Notes issued to registered taxpayers</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Name of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Reverse charge*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Supply Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cdnrData.length > 0 ? cdnrData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-gray-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.note_number,
                                                            type: 'Credit Note',
                                                            source: 'cdnr_drilldown'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.gstin}</td>
                                                <td className="px-4 py-2 border text-sm">{row.recipient_name}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.reverse_charge}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_supply_type}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.applicable_tax_rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={13} className="px-4 py-8 text-center text-gray-500">
                                                    No CDNR data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'CDNRA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">CDNRA - Credit/Debit Notes (Registered) Amendment</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended Credit/Debit Notes issued to registered taxpayers</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Name of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Reverse charge*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Supply Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Amendment Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cdnraData.length > 0 ? cdnraData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-blue-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.original_note_number,
                                                            type: 'Credit Note',
                                                            source: 'cdnr_drilldown',
                                                            _viewAsGSTFiled: true
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.gstin || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.recipient_name || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_type || 'C'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply || ''}</td>
                                                <td className="px-4 py-2 border text-sm">{row.reverse_charge || 'N'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_supply_type || ''}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.applicable_tax_rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm" onClick={(e) => e.stopPropagation()}>
                                                    {row.amendment_filed ? (
                                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            ✅ Filed
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            Pending
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={16} className="px-4 py-8 text-center text-gray-500">
                                                    No CDNRA data available for selected period.
                                                </td>
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
                            <p className="text-sm text-gray-600 mb-4">Credit and Debit Notes issued to unregistered taxpayers</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">UR Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cdnurData.length > 0 ? cdnurData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-gray-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.note_number,
                                                            type: 'Credit Note',
                                                            source: 'cdnur_drilldown'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.ur_type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.applicable_tax_rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                                                    No CDNUR data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'CDNURA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">CDNURA - Credit/Debit Notes (Unregistered) Amendment</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended Credit/Debit Notes issued to unregistered taxpayers</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">UR Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Note Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Note date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Note value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Amendment Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cdnuraData.length > 0 ? cdnuraData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-blue-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.original_note_number,
                                                            type: 'Credit Note',
                                                            source: 'cdnur_drilldown',
                                                            _viewAsGSTFiled: true
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.ur_type || 'B2CL'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_note_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_note_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.note_type || 'C'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply || ''}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.note_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.applicable_tax_rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm" onClick={(e) => e.stopPropagation()}>
                                                    {row.amendment_filed ? (
                                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            ✅ Filed
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            Pending
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={13} className="px-4 py-8 text-center text-gray-500">
                                                    No CDNURA data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'AT' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">AT - Advance Tax</h3>
                            <p className="text-sm text-gray-600 mb-4">Tax collected in advance (TCS/TDS)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply(POS)*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Gross advance received*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {atData.length > 0 ? atData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-gray-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.voucher_no,
                                                            type: 'Receipt',
                                                            source: 'receipt_voucher',
                                                            gst_registered: row.gst_registered,
                                                            _viewAsGSTFiled: row.gst_registered === 'Yes'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.gross_advance_received).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                    No AT data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ATA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ATA - Advance Tax (Amendment)</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended Tax collected in advance</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Financial Year</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Month*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Place of Supply(POS)*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Place of Supply(POS)*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Gross advance received*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ataData.length > 0 ? ataData.map((row, idx) => (
                                            <tr
                                                key={idx}
                                                className="hover:bg-indigo-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.voucher_no,
                                                            type: 'Receipt',
                                                            source: 'receipt_voucher',
                                                            gst_registered: row.gst_registered,
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.original_year}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_month}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_pos}</td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_pos}</td>
                                                <td className="px-4 py-2 border text-sm"></td>
                                                <td className="px-4 py-2 border text-sm">{row.revised_rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.revised_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm" onClick={(e) => e.stopPropagation()}>
                                                    {row.amendment_filed ? (
                                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            ✅ Filed
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase tracking-wider whitespace-nowrap">
                                                            Pending
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                                                    No ATA data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}


                    {!isLoading && activeSubTab === 'ATADJ' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ATADJ - Advance Tax Adjustment</h3>
                            <p className="text-sm text-gray-600 mb-4">Adjustment of advance tax paid</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply(POS)*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Gross advance received*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {atadjData.length > 0 ? atadjData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-blue-50 cursor-pointer transition-colors"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            id: row.voucher_id,
                                                            voucherNo: row.voucher_no,
                                                            type: 'Sales',
                                                            source: 'atadj_drilldown',
                                                            _viewAsGSTFiled: true 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.gross_advance_received).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                    No ATADJ data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'EXPA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-1">EXPA - Amended Export Invoices</h3>
                            <p className="text-sm text-gray-600 mb-4">GST-filed export invoices that were subsequently edited. Shows the <strong>original filed values</strong> and the <strong>revised (amended) values</strong>.</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Export Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium bg-amber-50">Original Invoice No.*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium bg-amber-50">Original Invoice Date*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium bg-blue-50">Revised Invoice No.*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium bg-blue-50">Revised Invoice Date*</th>
                                            <th className="px-4 py-2 border text-right text-sm font-medium">Invoice Value*</th>
                                            <th className="px-4 py-2 border text-right text-sm font-medium">Taxable Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Port Code</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SB Number</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SB Date</th>
                                            <th className="px-4 py-2 border text-center text-sm font-medium">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {expaData.length > 0 ? expaData.map((row, idx) => (
                                            <tr
                                                key={idx}
                                                className="hover:bg-amber-50 cursor-pointer"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.revised_invoice_no,
                                                            type: 'Sales',
                                                            source: 'exp_drilldown',
                                                            _viewAsGSTFiled: true
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.export_type}</td>
                                                <td className="px-4 py-2 border text-sm font-medium text-amber-700 bg-amber-50">{row.original_invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm text-gray-500 bg-amber-50">{row.original_invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm font-medium text-blue-700 bg-blue-50">{row.revised_invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm text-blue-500 bg-blue-50">{row.revised_invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.port_code || '—'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.shipping_bill_number || '—'}</td>
                                                <td className="px-4 py-2 border text-sm">{row.shipping_bill_date || '—'}</td>
                                                <td className="px-4 py-2 border text-sm text-center">
                                                    {row.amendment_filed ? (
                                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase whitespace-nowrap">Filed</span>
                                                    ) : (
                                                        <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase whitespace-nowrap">Pending</span>
                                                    )}
                                                </td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                                    No EXPA data available for selected period. Amended export invoices will appear here.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}



                    {!isLoading && activeSubTab === 'ATADJA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ATADJA - Advance Tax Adjustment (Amendment)</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended Adjustment of tax liability for tax already paid on advance received</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Financial Year</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Month*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Place of Supply(POS)*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Applicable % of Tax Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Gross advance adjusted*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {atadjaData.length > 0 ? atadjaData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className="hover:bg-blue-50 cursor-pointer transition-colors"
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            id: row.voucher_id,
                                                            voucherNo: row.voucher_no,
                                                            type: 'Sales',
                                                            source: 'atadj_drilldown',
                                                            _viewAsGSTFiled: true 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{period.year}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_month}</td>
                                                <td className="px-4 py-2 border text-sm">{row.original_place_of_supply}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.gross_advance_adjusted).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                                                    No ATADJA data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECO' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECO - E-Commerce Operator</h3>
                            <p className="text-sm text-gray-600 mb-4">Supplies through E-C Details of supplies through Electronic Commerce Operator</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Nature of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply(POS)/ GSTIN*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">E-Commerce Operator Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Net value of supplies*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Integrated Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Central Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">State/UT Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecoData.length === 0 ? (
                                            <tr>
                                                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                                                    No ECO data available for selected period.
                                                </td>
                                            </tr>
                                        ) : (
                                            ecoData.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedEcoRow(row)}>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.nature_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.ecommerce_name}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.net_value || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.igst || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.cgst || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.sgst || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.cess || 0).toFixed(2)}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOA - Amended E-Commerce Operator</h3>
                            {ecoaData.length > 0 ? (
                                <div className="table-responsive">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th>Original ECO GSTIN</th>
                                                <th>Revised ECO GSTIN</th>
                                                <th>Total Taxable Value</th>
                                                <th>Total IGST</th>
                                                <th>Total CGST</th>
                                                <th>Total SGST</th>
                                                <th>Total CESS</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {ecoaData.map((row, index) => (
                                                <tr key={index} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedEcoRow(row)}>
                                                    <td>{row.original_ecommerce_gstin || '-'}</td>
                                                    <td>{row.ecommerce_gstin || '-'}</td>
                                                    <td>{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td>{Number(row.igst).toFixed(2)}</td>
                                                    <td>{Number(row.cgst).toFixed(2)}</td>
                                                    <td>{Number(row.sgst).toFixed(2)}</td>
                                                    <td>{Number(row.cess).toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot>
                                            <tr className="font-semibold bg-gray-50">
                                                <td colSpan={2} className="text-right">Total:</td>
                                                <td>{Number(ecoaData.reduce((sum, row) => sum + (Number(row.taxable_value) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoaData.reduce((sum, row) => sum + (Number(row.igst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoaData.reduce((sum, row) => sum + (Number(row.cgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoaData.reduce((sum, row) => sum + (Number(row.sgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoaData.reduce((sum, row) => sum + (Number(row.cess) || 0), 0)).toFixed(2)}</td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            ) : (
                                <div className="erp-empty-state">
                                    <div className="erp-empty-state-icon">📊</div>
                                    <h4 className="erp-empty-state-title">No Amended E-Commerce Data</h4>
                                    <p className="erp-empty-state-desc">No amended transactions through e-commerce operators found for this period.</p>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOB2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOB2B - Supplies UIA 9/5</h3>
                            <p className="text-sm text-gray-600 mb-4">Details of supplies (via E-Commerce) 15 B2B</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Supplier</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Recipient Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Number</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Value of supplies made</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Supply Type*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document type</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecob2bData.length === 0 ? (
                                            <tr>
                                                <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOB2B data available for selected period.
                                                </td>
                                            </tr>
                                        ) : (
                                            ecob2bData.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.invoice_no,
                                                            type: 'Sales',
                                                            source: row.source || 'ecob2b_drilldown',
                                                            _viewAsGSTFiled: false 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.supplier_gstin}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.recipient_gstin}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.recipient_name}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.invoice_no}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.invoice_date}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.invoice_value || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.supply_type}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.document_type}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.rate}%</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.cess || 0).toFixed(2)}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOURP2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOURP2B - Supplies via E-Commerce to URP B2B</h3>
                            <p className="text-sm text-gray-600 mb-4">Details of supplies made through e-commerce to unregistered persons (B2B)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Recipient Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document Number</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Value of Supplies Made</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document Type</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecourp2bData.length === 0 ? (
                                            <tr>
                                                <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOURP2B data available for selected period.
                                                </td>
                                            </tr>
                                        ) : (
                                            ecourp2bData.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.invoice_no,
                                                            type: 'Sales',
                                                            source: row.source || 'ecourp2b_drilldown',
                                                            _viewAsGSTFiled: false 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td className="px-4 py-2 border text-sm">{row.recipient_gstin}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.recipient_name}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">₹{Number(row.invoice_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm">{row.document_type}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{row.rate}%</td>
                                                    <td className="px-4 py-2 border text-sm text-right">₹{Number(row.taxable_value).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">₹{Number(row.cess).toFixed(2)}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOB2C' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOB2C - Supplies via E-Commerce to B2C</h3>
                            <p className="text-sm text-gray-600 mb-4">Details of supplies made through e-commerce to consumers (B2C)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Supplier</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Supplier Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecob2cData.length === 0 ? (
                                            <tr>
                                                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOB2C data available for selected period.
                                                </td>
                                            </tr>
                                        ) : (
                                            ecob2cData.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            type: 'Sales',
                                                            source: row.source || 'ecob2c_drilldown',
                                                            _viewAsGSTFiled: false 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.supplier_gstin}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.supplier_name}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">{row.rate}%</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-gray-700">₹{Number(row.cess || 0).toFixed(2)}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOURP2C' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOURP2C - Supplies via E-Commerce to URP B2C</h3>
                            <p className="text-sm text-gray-600 mb-4">Details of supplies made through e-commerce to unregistered persons (B2C)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecourp2cData.length === 0 ? (
                                            <tr>
                                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOURP2C data available for selected period.
                                                </td>
                                            </tr>
                                        ) : (
                                            ecourp2cData.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.invoice_no || '',
                                                            type: 'Sales',
                                                            source: row.source || 'ecourp2c_drilldown',
                                                            _viewAsGSTFiled: false 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td className="px-4 py-2 border text-sm">{row.place_of_supply}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">{row.rate}%</td>
                                                    <td className="px-4 py-2 border text-sm text-right">₹{Number(row.taxable_value || 0).toFixed(2)}</td>
                                                    <td className="px-4 py-2 border text-sm text-right">₹{Number(row.cess || 0).toFixed(2)}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOAB2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOAB2B - Amended ECO B2B Invoices</h3>
                            {ecoab2bData.length > 0 ? (
                                <div className="table-responsive">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th>Original Customer GSTIN</th>
                                                <th>Revised Customer GSTIN</th>
                                                <th>Original Invoice No</th>
                                                <th>Revised Invoice No</th>
                                                <th>ECO GSTIN</th>
                                                <th>Original POS</th>
                                                <th>Revised POS</th>
                                                <th>Rate</th>
                                                <th>Original Taxable</th>
                                                <th>Revised Taxable</th>
                                                <th>IGST</th>
                                                <th>CGST</th>
                                                <th>SGST</th>
                                                <th>CESS</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {ecoab2bData.map((row, index) => (
                                                <tr key={index} className="cursor-pointer hover:bg-gray-50" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.revised_invoice_no,
                                                            type: 'Sales',
                                                            source: row.source || 'ecoab2b_drilldown',
                                                            _viewAsGSTFiled: true 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td>{row.original_customer_gstin || '-'}</td>
                                                    <td>{row.revised_customer_gstin || '-'}</td>
                                                    <td>{row.original_invoice_no || '-'}</td>
                                                    <td>{row.revised_invoice_no || '-'}</td>
                                                    <td>{row.ecommerce_gstin || '-'}</td>
                                                    <td>{row.original_pos || '-'}</td>
                                                    <td>{row.revised_pos || '-'}</td>
                                                    <td>{row.rate}%</td>
                                                    <td>{Number(row.original_taxable_value).toFixed(2)}</td>
                                                    <td>{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                    <td>{Number(row.igst).toFixed(2)}</td>
                                                    <td>{Number(row.cgst).toFixed(2)}</td>
                                                    <td>{Number(row.sgst).toFixed(2)}</td>
                                                    <td>{Number(row.cess).toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot>
                                            <tr className="font-semibold bg-gray-50">
                                                <td colSpan={8} className="text-right">Total:</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.original_taxable_value) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.revised_taxable_value) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.igst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.cgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.sgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2bData.reduce((sum, row) => sum + (Number(row.cess) || 0), 0)).toFixed(2)}</td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            ) : (
                                <div className="erp-empty-state">
                                    <div className="erp-empty-state-icon">📄</div>
                                    <h4 className="erp-empty-state-title">No Amended B2B E-Commerce Data</h4>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOAB2C' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOAB2C - Amended ECO B2C Invoices</h3>
                            {ecoab2cData.length > 0 ? (
                                <div className="table-responsive">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th>Original POS</th>
                                                <th>Revised POS</th>
                                                <th>Original Invoice No</th>
                                                <th>Revised Invoice No</th>
                                                <th>ECO GSTIN</th>
                                                <th>Rate</th>
                                                <th>Original Taxable</th>
                                                <th>Revised Taxable</th>
                                                <th>IGST</th>
                                                <th>CGST</th>
                                                <th>SGST</th>
                                                <th>CESS</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {ecoab2cData.map((row, index) => (
                                                <tr key={index} className="cursor-pointer hover:bg-gray-50" onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({ 
                                                            ...row, 
                                                            voucherNo: row.revised_invoice_no,
                                                            type: 'Sales',
                                                            source: row.source || 'ecoab2c_drilldown',
                                                            _viewAsGSTFiled: true 
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}>
                                                    <td>{row.original_pos || '-'}</td>
                                                    <td>{row.revised_pos || '-'}</td>
                                                    <td>{row.original_invoice_no || '-'}</td>
                                                    <td>{row.revised_invoice_no || '-'}</td>
                                                    <td>{row.ecommerce_gstin || '-'}</td>
                                                    <td>{row.rate}%</td>
                                                    <td>{Number(row.original_taxable_value).toFixed(2)}</td>
                                                    <td>{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                    <td>{Number(row.igst).toFixed(2)}</td>
                                                    <td>{Number(row.cgst).toFixed(2)}</td>
                                                    <td>{Number(row.sgst).toFixed(2)}</td>
                                                    <td>{Number(row.cess).toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot>
                                            <tr className="font-semibold bg-gray-50">
                                                <td colSpan={6} className="text-right">Total:</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.original_taxable_value) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.revised_taxable_value) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.igst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.cgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.sgst) || 0), 0)).toFixed(2)}</td>
                                                <td>{Number(ecoab2cData.reduce((sum, row) => sum + (Number(row.cess) || 0), 0)).toFixed(2)}</td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            ) : (
                                <div className="erp-empty-state">
                                    <div className="erp-empty-state-icon">📄</div>
                                    <h4 className="erp-empty-state-title">No Amended B2C E-Commerce Data</h4>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOAURP2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOAURP2B - Amended Supplies via E-Commerce to URP B2B</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended details of supplies made through e-commerce to unregistered persons (B2B)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN/UIN of Recipient</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Recipient Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Document Number</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Document Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Document Number</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Revised Document Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Value of Supplies Made</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Document Type</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecoaurp2bData.length > 0 ? ecoaurp2bData.map((row, index) => (
                                            <tr key={index} className="cursor-pointer hover:bg-gray-50" onClick={() => {
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({ 
                                                        ...row, 
                                                        voucherNo: row.revised_invoice_no,
                                                        type: 'Sales',
                                                        source: row.source || 'ecoaurp2b_drilldown',
                                                        _viewAsGSTFiled: true 
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}>
                                                <td>{row.revised_customer_gstin || '-'}</td>
                                                <td>{row.revised_customer_name || '-'}</td>
                                                <td>{row.original_invoice_no || '-'}</td>
                                                <td>{row.original_invoice_date || '-'}</td>
                                                <td>{row.revised_invoice_no || '-'}</td>
                                                <td>{row.revised_invoice_date || '-'}</td>
                                                <td>{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                <td>{row.revised_pos || '-'}</td>
                                                <td>Invoice</td>
                                                <td>{row.rate}%</td>
                                                <td>{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                <td>{Number(row.cess).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOAURP2B data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'ECOAURP2C' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">ECOAURP2C - Amended Supplies via E-Commerce to URP B2C</h3>
                            <p className="text-sm text-gray-600 mb-4">Amended details of supplies made through e-commerce to unregistered persons (B2C)</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Financial Year*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Original Month*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Place Of Supply</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ecoaurp2cData.length > 0 ? ecoaurp2cData.map((row, index) => (
                                            <tr key={index} className="cursor-pointer hover:bg-gray-50" onClick={() => {
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({ 
                                                        ...row, 
                                                        voucherNo: row.revised_invoice_no,
                                                        type: 'Sales',
                                                        source: row.source || 'ecoaurp2c_drilldown',
                                                        _viewAsGSTFiled: true 
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}>
                                                <td>{period.year}</td>
                                                <td>{period.month}</td>
                                                <td>{row.revised_pos || '-'}</td>
                                                <td>{row.rate}%</td>
                                                <td>{Number(row.revised_taxable_value).toFixed(2)}</td>
                                                <td>{Number(row.cess).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                                                    No ECOAURP2C data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'EXEMP' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">EXEMP - Exempted Supplies</h3>
                            <p className="text-sm text-gray-600 mb-4">Details of exempted, nil-rated and non-GST supplies</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Description</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Nil rated supplies</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Exempted</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Non GST Supplies</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {exempData.length > 0 ? exempData.map((row, idx) => (
                                            <tr key={idx} 
                                                className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                                onClick={() => {
                                                    if (row.vouchers && row.vouchers.length > 0) {
                                                        setSelectedExempRow(row);
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.description}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.nil_rated_supplies || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.exempted || 0).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.non_gst_supplies || 0).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                    No EXEMP data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'DOC' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">DOC - Document Details</h3>
                            <p className="text-sm text-gray-600 mb-4">Summary of documents issued during the period</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Nature of Document*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Sr. No From*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Sr. No To*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Total Number*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cancelled</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {docData.length > 0 ? docData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleDocRowClick()}>
                                                <td className="px-4 py-2 border text-sm">{row.nature_of_document}</td>
                                                <td className="px-4 py-2 border text-sm">{row.sr_no_from}</td>
                                                <td className="px-4 py-2 border text-sm">{row.sr_no_to}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.total_number}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.cancelled || 0}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                                                    No DOC data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'EXP' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">Exports</h3>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Export Type</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Port Code</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SB No</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SB Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {expData.length > 0 ? expData.map((row, idx) => (
                                            <tr 
                                                key={idx} 
                                                className={`hover:bg-gray-50 cursor-pointer`}
                                                onClick={() => {
                                                    if (setViewVoucherData && onNavigate) {
                                                        setViewVoucherData({
                                                            ...row,
                                                            voucherNo: row.invoice_no,
                                                            type: 'Sales',
                                                            source: 'exp_drilldown'
                                                        });
                                                        onNavigate('Vouchers');
                                                    }
                                                }}
                                            >
                                                <td className="px-4 py-2 border text-sm">{row.export_type}</td>
                                                <td className="px-4 py-2 border text-sm">{row.invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{row.invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.invoice_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm">{row.port_code}</td>
                                                <td className="px-4 py-2 border text-sm">{row.shipping_bill_number}</td>
                                                <td className="px-4 py-2 border text-sm">{row.shipping_bill_date}</td>
                                                <td className="px-4 py-2 border text-sm">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                                                    No export invoices found.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}



                    {!isLoading && activeSubTab === 'HSNB2B' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">HSN Summary of B2B</h3>
                            <p className="text-sm text-gray-600 mb-4">HSN wise summary of goods/services supplied during the tax period</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">HSN*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Description</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">UQC*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Total Quantity*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Total Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Integrated Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Central Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">State/UT Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {hsnB2bData.length > 0 ? hsnB2bData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleHsnRowClick(row, true)}>
                                                <td className="px-4 py-2 border text-sm text-[#3b2ddb]">{row.hsn}</td>
                                                <td className="px-4 py-2 border text-sm">{row.description}</td>
                                                <td className="px-4 py-2 border text-sm">{row.uqc}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.total_quantity}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.total_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.integrated_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.central_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.state_ut_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                                    No HSNB2B data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'HSNB2C' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">HSN Summary of B2C</h3>
                            <p className="text-sm text-gray-600 mb-4">HSN wise summary of goods/services supplied during the tax period</p>
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">HSN*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Description</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">UQC*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Total Quantity*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Total Value</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Rate</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Value*</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Integrated Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Central Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">State/UT Tax Amount</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Cess Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {hsnB2cData.length > 0 ? hsnB2cData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleHsnRowClick(row, false)}>
                                                <td className="px-4 py-2 border text-sm text-[#3b2ddb]">{row.hsn}</td>
                                                <td className="px-4 py-2 border text-sm">{row.description}</td>
                                                <td className="px-4 py-2 border text-sm">{row.uqc}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.total_quantity}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.total_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{row.rate}%</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.integrated_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.central_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.state_ut_tax_amount).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(row.cess_amount).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                                    No HSNB2C data available for selected period.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && !['B2B', 'B2BA', 'B2CL', 'B2CLA', 'B2CS', 'B2CSA', 'CDNR', 'CDNRA', 'CDNUR', 'CDNURA', 'EXP', 'EXPA', 'AT', 'ATA', 'ATADJ', 'ATADJA', 'ECO', 'ECOA', 'ECOB2B', 'ECOURP2B', 'ECOB2C', 'ECOURP2C', 'ECOAB2B', 'ECOAB2C', 'ECOAURP2B', 'ECOAURP2C', 'EXEMP', 'HSNB2B', 'HSNB2C', 'DOC'].includes(activeSubTab) && (
                        <div className="text-center py-12">
                            <p className="text-gray-500">This sub-tab is under development.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* DOC Drilldown Modal */}
            {showDocDrilldown && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50 px-4">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
                        <div className="px-6 py-4 border-b flex justify-between items-center bg-gray-50 rounded-t-lg">
                            <div>
                                <h3 className="text-lg font-bold text-gray-800">DOC - Document Details</h3>
                                <p className="text-sm text-gray-500">All invoices issued during this period</p>
                            </div>
                            <button onClick={() => setShowDocDrilldown(false)} className="text-gray-500 hover:bg-gray-200 p-2 rounded-full transition-colors">
                                <span className="material-icons-outlined">close</span>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto flex-1">
                            {docDrilldownLoading ? (
                                <div className="flex justify-center items-center py-10">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                                </div>
                            ) : (
                                <div className="erp-table-container">
                                    <table className="erp-table">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Date</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Customer Name</th>
                                                <th className="px-4 py-2 border text-left text-sm font-medium">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {docDrilldownData.length > 0 ? docDrilldownData.map((inv, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50">
                                                    <td className="px-4 py-2 border text-sm text-indigo-600 cursor-pointer hover:underline" onClick={() => {
                                                        setShowDocDrilldown(false);
                                                        onNavigate?.('vouchers', { highlightInvoice: inv.invoice_no, salesPk: inv.id, type: 'sales' });
                                                    }}>
                                                        {inv.invoice_no}
                                                    </td>
                                                    <td className="px-4 py-2 border text-sm">{inv.invoice_date}</td>
                                                    <td className="px-4 py-2 border text-sm">{inv.customer_name}</td>
                                                    <td className="px-4 py-2 border text-sm">
                                                        {inv.status === 'cancelled' ? (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                                                                Cancelled
                                                            </span>
                                                        ) : (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                                Valid
                                                            </span>
                                                        )}
                                                    </td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                        No documents found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* HSN Drilldown Modal */}
            {showHsnDrilldown && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl w-[900px] max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-xl font-bold text-[#3b2ddb]">
                                    Invoices for HSN: {currentHsnParams?.hsn} (Rate: {currentHsnParams?.rate}%)
                                </h3>
                                <p className="text-xs text-gray-500 mt-1">
                                    {currentHsnParams?.isB2b ? 'B2B Supplies' : 'B2C Supplies'}
                                </p>
                            </div>
                            <button onClick={() => setShowHsnDrilldown(false)} className="text-gray-500 hover:text-gray-700">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {hsnDrilldownLoading ? (
                            <div className="flex justify-center py-10">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3b2ddb]"></div>
                            </div>
                        ) : (
                            <div className="erp-table-container">
                                <table className="erp-table">
                                    <thead>
                                        <tr>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Invoice No</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Date</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Customer Name</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">GSTIN</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">Taxable Val</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">IGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">CGST</th>
                                            <th className="px-4 py-2 border text-left text-sm font-medium">SGST</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {hsnDrilldownData.length > 0 ? hsnDrilldownData.map((inv, idx) => (
                                            <tr key={idx} className="hover:bg-gray-50 cursor-pointer" onClick={() => {
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({ 
                                                        voucherId: inv.voucher_pk || inv.id, 
                                                        reference_id: inv.reference_id || inv.id,
                                                        voucher_pk: inv.voucher_pk,
                                                        voucherNo: inv.invoice_no, 
                                                        type: 'Sales', 
                                                        source: 'hsn_drilldown' 
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}>
                                                <td className="px-4 py-2 border text-sm font-medium text-[#3b2ddb]">{inv.invoice_no}</td>
                                                <td className="px-4 py-2 border text-sm">{inv.invoice_date}</td>
                                                <td className="px-4 py-2 border text-sm">{inv.customer_name}</td>
                                                <td className="px-4 py-2 border text-sm">{inv.gstin}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(inv.taxable_value).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(inv.igst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(inv.cgst).toFixed(2)}</td>
                                                <td className="px-4 py-2 border text-sm text-right">{Number(inv.sgst).toFixed(2)}</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                                                    No invoices found for this HSN.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-xl">
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">Edit Invoice</h3>
                        <p className="text-sm text-gray-600 mb-6">This is already registered. You can't edit it.</p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    if (selectedInvoice) {
                                        setAmendmentForm({
                                            original_invoice_no: selectedInvoice.invoice_no,
                                            original_invoice_date: selectedInvoice.invoice_date,
                                            original_invoice_value: selectedInvoice.invoice_value,
                                            original_taxable_value: selectedInvoice.taxable_value,
                                            revised_invoice_no: selectedInvoice.invoice_no,
                                            revised_invoice_date: selectedInvoice.invoice_date,
                                            revised_invoice_value: selectedInvoice.invoice_value,
                                            revised_taxable_value: selectedInvoice.taxable_value,
                                            recipient_name: selectedInvoice.recipient_name || '',
                                            place_of_supply: selectedInvoice.place_of_supply || '',
                                            reverse_charge: selectedInvoice.reverse_charge || 'N',
                                        });
                                        setShowAmendmentModal(true);
                                    }
                                    setShowEditModal(false);
                                }}
                                className="px-4 py-2 bg-[#3b2ddb] text-white rounded-md hover:bg-[#3b2ddb]/90 font-medium text-sm"
                            >
                                EDIT ANYWAY
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Amendment Form Modal */}
            {showAmendmentModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl w-[600px] max-h-[90vh] overflow-y-auto">
                        <h3 className="text-xl font-bold mb-4 text-[#3b2ddb]">Amend B2B Invoice</h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Original Invoice No</label>
                                <input type="text" className="w-full border rounded p-2 bg-gray-100 text-gray-600 outline-none" readOnly value={amendmentForm.original_invoice_no || ''} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Original Invoice Date</label>
                                <input type="text" className="w-full border rounded p-2 bg-gray-100 text-gray-600 outline-none" readOnly value={amendmentForm.original_invoice_date || ''} />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Revised Invoice No <span className="text-red-500">*</span></label>
                                <input type="text" className="w-full border rounded p-2 outline-none" value={amendmentForm.revised_invoice_no || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, revised_invoice_no: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Revised Invoice Date <span className="text-red-500">*</span></label>
                                <input type="date" className="w-full border rounded p-2 outline-none" value={amendmentForm.revised_invoice_date || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, revised_invoice_date: e.target.value })} />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Revised Invoice Value <span className="text-red-500">*</span></label>
                                <input type="number" step="0.01" className="w-full border rounded p-2 outline-none" value={amendmentForm.revised_invoice_value || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, revised_invoice_value: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Revised Taxable Value <span className="text-red-500">*</span></label>
                                <input type="number" step="0.01" className="w-full border rounded p-2 outline-none" value={amendmentForm.revised_taxable_value || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, revised_taxable_value: e.target.value })} />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Recipient Name <span className="text-red-500">*</span></label>
                                <input type="text" className="w-full border rounded p-2 outline-none" value={amendmentForm.recipient_name || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, recipient_name: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Place of Supply <span className="text-red-500">*</span></label>
                                <input type="text" className="w-full border rounded p-2 outline-none" value={amendmentForm.place_of_supply || ''} onChange={(e) => setAmendmentForm({ ...amendmentForm, place_of_supply: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-gray-700">Reverse Charge <span className="text-red-500">*</span></label>
                                <select className="w-full border rounded p-2 outline-none" value={amendmentForm.reverse_charge || 'N'} onChange={(e) => setAmendmentForm({ ...amendmentForm, reverse_charge: e.target.value })}>
                                    <option value="N">N</option>
                                    <option value="Y">Y</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex justify-end space-x-4 mt-6">
                            <button
                                className="px-4 py-2 border rounded text-gray-600 hover:bg-gray-50 font-medium text-sm"
                                onClick={() => setShowAmendmentModal(false)}
                            >
                                CANCEL
                            </button>
                            <button
                                className="px-4 py-2 bg-[#3b2ddb] text-white rounded hover:bg-[#3b2ddb]/90 font-medium text-sm"
                                onClick={() => {
                                    setB2baData(prev => [...prev, amendmentForm]);
                                    setB2bData(prev => prev.filter(item => item.invoice_no !== amendmentForm.original_invoice_no));
                                    setShowAmendmentModal(false);
                                    setActiveSubTab('B2BA');
                                }}
                            >
                                SAVE AMENDMENT
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {viewAmendmentData && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl w-[700px] max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-xl font-bold text-[#3b2ddb]">Amendmented Voucher Details</h3>
                                <p className="text-xs text-gray-500 mt-1">Showing the revised/amended values of this invoice</p>
                            </div>
                            <button onClick={() => setViewAmendmentData(null)} className="text-gray-500 hover:text-gray-700">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>

                        {/* Original Section */}
                        <div className="mb-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                            <div className="flex items-center mb-3">
                                <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full mr-2">✓ GST FILED (Original)</span>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Invoice No</label>
                                    <p className="text-sm font-semibold text-gray-800">{viewAmendmentData.original_invoice_no}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Invoice Date</label>
                                    <p className="text-sm font-semibold text-gray-800">{viewAmendmentData.original_invoice_date}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Invoice Value</label>
                                    <p className="text-sm font-semibold text-gray-800">{Number(viewAmendmentData.invoice_value || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Taxable Value</label>
                                    <p className="text-sm font-semibold text-gray-800">{Number(viewAmendmentData.taxable_value || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">IGST</label>
                                    <p className="text-sm font-semibold text-gray-800">{Number(viewAmendmentData.igst || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">CGST / SGST</label>
                                    <p className="text-sm font-semibold text-gray-800">{Number(viewAmendmentData.cgst || 0).toFixed(2)} / {Number(viewAmendmentData.sgst || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Customer (GSTIN)</label>
                                    <p className="text-sm font-semibold text-gray-800">{viewAmendmentData.recipient_name} ({viewAmendmentData.gstin})</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500">Place of Supply</label>
                                    <p className="text-sm font-semibold text-gray-800">{viewAmendmentData.place_of_supply}</p>
                                </div>
                            </div>
                        </div>

                        {/* Arrow */}
                        <div className="flex items-center justify-center my-3">
                            <div className="flex items-center space-x-2 text-gray-400">
                                <div className="h-px w-24 bg-gray-300"></div>
                                <span className="text-sm font-medium text-gray-500">Amended to ↓</span>
                                <div className="h-px w-24 bg-gray-300"></div>
                            </div>
                        </div>

                        {/* Amended Section */}
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-center mb-3">
                                <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full mr-2">✎ AMENDED (Revised)</span>
                                <span className="text-xs text-gray-500">Amendment Date: {viewAmendmentData.revised_invoice_date}</span>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Invoice No</label>
                                    <p className="text-sm font-semibold text-indigo-700">{viewAmendmentData.amended_invoice_no || viewAmendmentData.revised_invoice_no}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Invoice Date</label>
                                    <p className="text-sm font-semibold text-indigo-700">{viewAmendmentData.amended_invoice_date || viewAmendmentData.revised_invoice_date}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Invoice Value</label>
                                    <p className="text-sm font-semibold text-indigo-700">{Number(viewAmendmentData.amended_invoice_value || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Taxable Value</label>
                                    <p className="text-sm font-semibold text-indigo-700">{Number(viewAmendmentData.amended_taxable_value || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">IGST</label>
                                    <p className="text-sm font-semibold text-indigo-700">{Number(viewAmendmentData.amended_igst || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">CGST / SGST</label>
                                    <p className="text-sm font-semibold text-indigo-700">{Number(viewAmendmentData.amended_cgst || 0).toFixed(2)} / {Number(viewAmendmentData.amended_sgst || 0).toFixed(2)}</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Customer (GSTIN)</label>
                                    <p className="text-sm font-semibold text-indigo-700">{viewAmendmentData.amended_recipient_name || viewAmendmentData.recipient_name} ({viewAmendmentData.amended_gstin || viewAmendmentData.gstin})</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-indigo-500">Place of Supply</label>
                                    <p className="text-sm font-semibold text-indigo-700">{viewAmendmentData.amended_place_of_supply || viewAmendmentData.place_of_supply}</p>
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end mt-6">
                            <button 
                                className="px-4 py-2 bg-[#3b2ddb] text-white rounded hover:bg-[#3b2ddb]/90 font-medium text-sm"
                                onClick={() => setViewAmendmentData(null)}
                            >
                                CLOSE
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* OTP Modal — shared for normal filing & amendment filing */}
            {showOtpModal && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col">
                        <div className={`px-6 py-4 border-b border-slate-100 flex items-center justify-between ${isAmendmentMode ? 'bg-amber-50' : 'bg-slate-50'}`}>
                            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <span className={isAmendmentMode ? 'text-amber-600' : 'text-emerald-600'}>
                                    {isAmendmentMode ? '📝' : '🛡️'}
                                </span>
                                {isAmendmentMode ? `File Amendment Return — ${activeSubTab}` : 'Taxpayer Authentication'}
                            </h3>
                            <button onClick={() => setShowOtpModal(false)} className="text-slate-400 hover:text-slate-600 p-1">
                                ✕
                            </button>
                        </div>
                        <div className="p-6">
                            {isAmendmentMode ? (
                                <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                                    <p className="text-sm font-semibold text-amber-800 mb-1">
                                        📋 You are filing an <strong>{activeSubTab}</strong> Amendment Return
                                    </p>
                                    <p className="text-xs text-amber-700">
                                        This will submit all pending {activeSubTab === 'EXPA' ? 'amended export invoices' : activeSubTab === 'ATADJA' ? 'amended advance adjustments' : 'B2B amended invoices'} for <strong>{period.month} {period.year}</strong> to the GST portal and clear them from this tab.
                                    </p>
                                </div>
                            ) : (
                                <p className="text-sm text-slate-600 mb-6">
                                    To file this return securely, you must authorize this action using the One-Time Password (OTP) sent to the registered mobile number for GSTIN <span className="font-bold text-slate-800">{activeGstin || '29AAACQ3770E000'}</span>.
                                </p>
                            )}

                            {!otpSent ? (
                                <div className="flex flex-col items-center">
                                    <button
                                        onClick={handleRequestOTP}
                                        disabled={isSendingOtp}
                                        className={`w-full py-3 text-white font-semibold rounded-xl transition-all ${isAmendmentMode ? 'bg-amber-600 hover:bg-amber-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                                    >
                                        {isSendingOtp ? 'Sending Request...' : 'Send OTP via SMS'}
                                    </button>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-700 mb-2">Enter 6-digit OTP</label>
                                        <input
                                            type="text"
                                            value={otpValue}
                                            onChange={(e) => setOtpValue(e.target.value)}
                                            placeholder="123456"
                                            className={`w-full px-4 py-3 bg-slate-50 border rounded-xl focus:ring-2 outline-none text-center tracking-widest text-lg font-mono ${isAmendmentMode ? 'border-amber-200 focus:ring-amber-400 focus:border-amber-400' : 'border-slate-200 focus:ring-emerald-500 focus:border-emerald-500'}`}
                                            maxLength={6}
                                        />
                                    </div>
                                    <button
                                        onClick={handleVerifyAndFile}
                                        disabled={isAmendmentMode ? isFilingAmendment : isFilingReturn}
                                        className={`w-full py-3 text-white font-semibold rounded-xl transition-all flex justify-center items-center gap-2 ${isAmendmentMode ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}
                                    >
                                        {(isAmendmentMode ? isFilingAmendment : isFilingReturn) ? (
                                            <>
                                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                {isAmendmentMode ? 'Filing Amendment...' : 'Verifying & Filing...'}
                                            </>
                                        ) : (isAmendmentMode ? `✅ Confirm & File Amendment (${activeSubTab})` : 'Verify & File Return')}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* ECO Drilldown Modal */}
            {selectedEcoRow && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                        <div className="flex justify-between items-center p-6 border-b border-gray-100">
                            <div>
                                <h3 className="text-xl font-bold text-gray-800">
                                    Invoices for {selectedEcoRow.ecommerce_name}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Place of Supply: {selectedEcoRow.place_of_supply} | Nature: {selectedEcoRow.nature_of_supply}
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedEcoRow(null)}
                                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <span className="material-icons-outlined">close</span>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            <table className="erp-table w-full">
                                <thead>
                                    <tr>
                                        <th className="px-4 py-3 bg-gray-50 border-b text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Invoice No.</th>
                                        <th className="px-4 py-3 bg-gray-50 border-b text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Date</th>
                                        <th className="px-4 py-3 bg-gray-50 border-b text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Invoice Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {selectedEcoRow.vouchers && selectedEcoRow.vouchers.map((v: any) => (
                                        <tr 
                                            key={v.id}
                                            className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                            onClick={() => {
                                                setSelectedEcoRow(null);
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({
                                                        voucher_pk: v.id,
                                                        voucherNo: v.invoice_no,
                                                        type: 'Sales',
                                                        source: v.source || 'eco_drilldown',
                                                        _viewAsGSTFiled: false
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}
                                        >
                                            <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.invoice_no}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-600">{v.invoice_date}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-600 text-right">₹{Number(v.invoice_value || 0).toFixed(2)}</td>
                                        </tr>
                                    ))}
                                    {(!selectedEcoRow.vouchers || selectedEcoRow.vouchers.length === 0) && (
                                        <tr>
                                            <td colSpan={3} className="px-4 py-8 text-center text-gray-500">
                                                No sub-vouchers found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* B2CS / B2CSA Sub-Vouchers Drilldown Modal */}
            {selectedB2csRow && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                        <div className="flex justify-between items-center p-6 border-b border-gray-100">
                            <div>
                                <h3 className="text-xl font-bold text-gray-800">
                                    Invoices for Place of Supply: {selectedB2csRow.place_of_supply || selectedB2csRow.revised_pos}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Click on an invoice to view or amend it.
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedB2csRow(null)}
                                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            <table className="erp-table w-full">
                                <thead>
                                    <tr>
                                        <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Invoice No</th>
                                        <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Date</th>
                                        <th className="px-4 py-3 border-b text-right text-sm font-semibold text-gray-600">Value</th>
                                        <th className="px-4 py-3 border-b text-center text-sm font-semibold text-gray-600">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(selectedB2csRow.vouchers || []).map((v: any) => (
                                        <tr
                                            key={v.id}
                                            className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                            onClick={() => {
                                                setSelectedB2csRow(null);
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({
                                                        ...v,
                                                        voucherNo: v.invoice_no,
                                                        type: 'Sales',
                                                        source: v.source,
                                                        _viewAsGSTFiled: v.amendment_date ? true : false
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}
                                        >
                                            <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.invoice_no}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-600">{v.invoice_date}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-800 text-right font-medium">₹{Number(v.invoice_value).toFixed(2)}</td>
                                            <td className="px-4 py-3 border-b text-sm text-center">
                                                {v.amendment_date ? (
                                                    <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase">Amended</span>
                                                ) : v.gst_registered === 'Yes' ? (
                                                    <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase">GST Filed</span>
                                                ) : (
                                                    <span className="px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-[10px] font-bold uppercase">Pending</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                    {(!selectedB2csRow.vouchers || selectedB2csRow.vouchers.length === 0) && (
                                        <tr>
                                            <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                No detailed invoices found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* EXEMP Drilldown Custom Modal */}
            {selectedExempRow && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                        <div className="flex justify-between items-center p-6 border-b border-gray-100">
                            <div>
                                <h3 className="text-xl font-bold text-gray-800">
                                    Vouchers for: {selectedExempRow.description}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Click on an invoice to view its details.
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedExempRow(null)}
                                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            <table className="erp-table w-full">
                                <thead>
                                    <tr>
                                        <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Invoice No</th>
                                        <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Date</th>
                                        <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Customer</th>
                                        <th className="px-4 py-3 border-b text-right text-sm font-semibold text-gray-600">Taxable Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(selectedExempRow.vouchers || []).map((v: any) => (
                                        <tr
                                            key={v.voucher_id}
                                            className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                            onClick={() => {
                                                setSelectedExempRow(null);
                                                if (setViewVoucherData && onNavigate) {
                                                    setViewVoucherData({
                                                        id: v.voucher_id,
                                                        voucherNo: v.voucher_no,
                                                        type: 'Sales',
                                                        source: 'exemp_drilldown',
                                                        _viewAsGSTFiled: false
                                                    });
                                                    onNavigate('Vouchers');
                                                }
                                            }}
                                        >
                                            <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.voucher_no}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-600">{v.date}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-600">{v.customer_name || 'Cash'}</td>
                                            <td className="px-4 py-3 border-b text-sm text-gray-800 text-right font-medium">₹{Number(v.total_taxable_value).toFixed(2)}</td>
                                        </tr>
                                    ))}
                                    {(!selectedExempRow.vouchers || selectedExempRow.vouchers.length === 0) && (
                                        <tr>
                                            <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                No detailed invoices found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


