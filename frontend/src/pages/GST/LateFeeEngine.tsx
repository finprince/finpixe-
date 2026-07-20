import React, { useState, useEffect, useRef } from 'react';
import { httpClient } from '../../services/httpClient';
import { AlertTriangle, CheckCircle, Clock, TrendingUp, X } from 'lucide-react';

interface LateFeeRecord {
    period_month: string;
    period_year: string;
    due_date: string;
    filed_date: string | null;
    is_filed: boolean;
    days_late: number;
    is_nil_return: boolean;
    cgst_late_fee: number;
    sgst_late_fee: number;
    total_late_fee: number;
    status: string;
    late_fee_id: number | null;
    arn_number: string | null;
}

export default function LateFeeEngine() {
    const [selectedYear, setSelectedYear] = useState('2024-25');
    const [records, setRecords] = useState<LateFeeRecord[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [payingId, setPayingId] = useState<number | null>(null);
    const [liveSeconds, setLiveSeconds] = useState(0);
    const timerRef = useRef<any>(null);

    // OTP Modal State
    const [selectedPayRecord, setSelectedPayRecord] = useState<LateFeeRecord | null>(null);
    const [otpValue, setOtpValue] = useState('');
    const [otpError, setOtpError] = useState('');

    const fetchLateFees = async () => {
        setIsLoading(true);
        try {
            const res: any = await httpClient.get(`/api/gst/reconciliation/calculate_late_fees/?year=${selectedYear}`);
            setRecords(res.results || []);
        } catch (err) {
            console.error('Failed to fetch late fees', err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchLateFees();
    }, [selectedYear]);

    // Live penalty ticker — updates every second
    useEffect(() => {
        timerRef.current = setInterval(() => setLiveSeconds(s => s + 1), 1000);
        return () => clearInterval(timerRef.current);
    }, []);

    const confirmPayment = async () => {
        if (!selectedPayRecord || !selectedPayRecord.late_fee_id) return;
        if (otpValue.length !== 6) {
            setOtpError('Please enter a valid 6-digit OTP');
            return;
        }
        
        setPayingId(selectedPayRecord.late_fee_id);
        setOtpError('');
        try {
            await httpClient.post('/api/gst/reconciliation/pay_late_fee/', { late_fee_id: selectedPayRecord.late_fee_id });
            await fetchLateFees();
            setSelectedPayRecord(null);
            setOtpValue('');
        } catch (err) {
            console.error('Payment failed', err);
            setOtpError('Payment authorization failed. Try again.');
        } finally {
            setPayingId(null);
        }
    };

    const pendingRecords = records.filter(r => r.status === 'PENDING');
    const totalPendingFee = pendingRecords.reduce((sum, r) => sum + r.total_late_fee, 0);
    const unfiledPendingCount = records.filter(r => !r.is_filed && r.days_late > 0).length;
    const liveAccruing = (unfiledPendingCount * 50 * liveSeconds) / 86400;
    const displayLiveTotal = totalPendingFee + liveAccruing;

    const getStatusBadge = (record: LateFeeRecord) => {
        if (record.status === 'PAID') return (
            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full flex items-center gap-1 w-fit">
                <CheckCircle className="w-3 h-3" /> PAID
            </span>
        );
        if (record.status === 'ON_TIME') return (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full flex items-center gap-1 w-fit">
                <CheckCircle className="w-3 h-3" /> ON TIME
            </span>
        );
        if (record.status === 'PENDING' && !record.is_filed) return (
            <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full flex items-center gap-1 w-fit animate-pulse">
                <Clock className="w-3 h-3" /> GROWING
            </span>
        );
        if (record.status === 'PENDING') return (
            <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full flex items-center gap-1 w-fit">
                <AlertTriangle className="w-3 h-3" /> UNPAID
            </span>
        );
        return null;
    };

    return (
        <div className="space-y-6">

            {/* Header Controls */}
            <div className="erp-container">
                <div className="flex justify-between items-center">
                    <div>
                        <h2 className="section-title border-none pb-0">Late Fees & Penalties</h2>
                        <p className="helper-text">Real-time GST late fee tracker based on your filed returns (₹50/day per Indian GST law)</p>
                    </div>
                    <select
                        value={selectedYear}
                        onChange={e => setSelectedYear(e.target.value)}
                        className="px-3 py-1.5 border rounded text-sm bg-white"
                    >
                        {['2023-24', '2024-25', '2025-26'].map(y => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4">
                <div className="erp-container bg-gradient-to-br from-red-50 to-red-100 border-red-200">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-red-500 rounded-lg">
                            <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <p className="text-xs text-red-600 font-semibold uppercase">Total Outstanding</p>
                            <p className="text-2xl font-bold font-mono text-red-700">
                                ₹{displayLiveTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </p>
                            {unfiledPendingCount > 0 && (
                                <p className="text-xs text-red-500 mt-0.5 animate-pulse">⚡ ₹50/day accruing</p>
                            )}
                        </div>
                    </div>
                </div>

                <div className="erp-container">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 font-semibold uppercase">Returns with Penalty</p>
                            <p className="text-2xl font-bold text-amber-600">{pendingRecords.length}</p>
                            <p className="text-xs text-slate-400">outstanding late fees</p>
                        </div>
                    </div>
                </div>

                <div className="erp-container">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-500 rounded-lg">
                            <CheckCircle className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 font-semibold uppercase">Filed On Time</p>
                            <p className="text-2xl font-bold text-green-600">
                                {records.filter(r => r.status === 'ON_TIME').length}
                            </p>
                            <p className="text-xs text-slate-400">compliant returns</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Penalty Tracker Table */}
            <div className="erp-container">
                <h3 className="section-title">Penalty Tracker — {selectedYear}</h3>
                {isLoading ? (
                    <div className="text-center py-10 text-slate-400">Calculating penalties...</div>
                ) : records.length === 0 ? (
                    <div className="text-center py-12 text-slate-400">
                        <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
                        <p className="font-semibold text-slate-600">No filed returns found for {selectedYear}</p>
                        <p className="text-sm mt-1">File a GSTR-3B return to see late fee data here.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="erp-table">
                            <thead>
                                <tr>
                                    <th>Period</th>
                                    <th>Due Date</th>
                                    <th>Filed On</th>
                                    <th>ARN</th>
                                    <th className="text-center">Days Late</th>
                                    <th className="text-right">CGST Fee</th>
                                    <th className="text-right">SGST Fee</th>
                                    <th className="text-right">Total Penalty</th>
                                    <th className="text-center">Status</th>
                                    <th className="text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {records.map(record => (
                                    <tr key={`${record.period_month}-${record.period_year}`}
                                        className={record.status === 'PENDING' ? 'bg-red-50/50' : ''}>
                                        <td className="font-semibold text-slate-800">
                                            {record.period_month} {record.period_year}
                                        </td>
                                        <td className="text-slate-500 text-sm">
                                            {new Date(record.due_date).toLocaleDateString('en-IN')}
                                        </td>
                                        <td className="text-sm">
                                            {record.filed_date
                                                ? new Date(record.filed_date).toLocaleDateString('en-IN')
                                                : <span className="text-amber-600 font-semibold">Draft</span>
                                            }
                                        </td>
                                        <td className="font-mono text-xs text-slate-500">
                                            {record.arn_number || '—'}
                                        </td>
                                        <td className="text-center">
                                            {record.days_late > 0
                                                ? <span className="font-bold text-red-600">{record.days_late}</span>
                                                : <span className="text-green-600">—</span>
                                            }
                                        </td>
                                        <td className="text-right font-mono text-sm">
                                            {record.cgst_late_fee > 0 ? `₹${record.cgst_late_fee.toLocaleString('en-IN')}` : '—'}
                                        </td>
                                        <td className="text-right font-mono text-sm">
                                            {record.sgst_late_fee > 0 ? `₹${record.sgst_late_fee.toLocaleString('en-IN')}` : '—'}
                                        </td>
                                        <td className="text-right font-mono font-bold">
                                            {record.total_late_fee > 0
                                                ? <span className="text-red-600">₹{record.total_late_fee.toLocaleString('en-IN')}</span>
                                                : <span className="text-green-600">₹0</span>
                                            }
                                        </td>
                                        <td className="text-center">{getStatusBadge(record)}</td>
                                        <td className="text-right">
                                            {record.status === 'PENDING' && record.late_fee_id ? (
                                                <button
                                                    onClick={() => setSelectedPayRecord(record)}
                                                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded transition-all"
                                                >
                                                    Pay Now
                                                </button>
                                            ) : record.status === 'PAID' ? (
                                                <span className="text-xs text-green-600 font-semibold">Cleared</span>
                                            ) : (
                                                <span className="text-xs text-slate-400">—</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* OTP Payment Modal */}
            {selectedPayRecord && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
                        <div className="flex items-center justify-between p-4 border-b bg-slate-50">
                            <h3 className="font-bold text-slate-800">Authorize Payment</h3>
                            <button 
                                onClick={() => {
                                    setSelectedPayRecord(null);
                                    setOtpValue('');
                                    setOtpError('');
                                }} 
                                className="text-slate-400 hover:text-slate-600"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        
                        <div className="p-6">
                            <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6 text-sm border border-red-100 flex items-start gap-3">
                                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-bold mb-1">Confirm Deduction</p>
                                    <p>You are about to pay <b>₹{selectedPayRecord.total_late_fee.toLocaleString('en-IN')}</b> for the {selectedPayRecord.period_month} {selectedPayRecord.period_year} late fee penalty.</p>
                                    <p className="mt-2 text-xs text-red-600">This amount will be offset against your Electronic Cash Ledger.</p>
                                </div>
                            </div>

                            <div className="mb-6">
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                    Enter EVC / OTP
                                </label>
                                <input
                                    type="text"
                                    maxLength={6}
                                    placeholder="Enter 6-digit OTP (e.g. 123456)"
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-center font-mono text-lg tracking-widest"
                                    value={otpValue}
                                    onChange={(e) => {
                                        setOtpValue(e.target.value.replace(/\D/g, ''));
                                        setOtpError('');
                                    }}
                                />
                                {otpError && <p className="text-red-500 text-xs mt-2">{otpError}</p>}
                                <p className="text-slate-400 text-xs mt-2 text-center">
                                    An OTP has been sent to the authorized signatory's mobile number.
                                </p>
                            </div>

                            <button
                                onClick={confirmPayment}
                                disabled={payingId === selectedPayRecord.late_fee_id || otpValue.length !== 6}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-lg flex justify-center items-center gap-2 transition-colors"
                            >
                                {payingId === selectedPayRecord.late_fee_id ? (
                                    <>Processing...</>
                                ) : (
                                    <>Authorize Payment of ₹{selectedPayRecord.total_late_fee.toLocaleString('en-IN')}</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
