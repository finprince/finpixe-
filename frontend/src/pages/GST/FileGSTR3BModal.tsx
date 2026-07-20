import React, { useState } from 'react';
import { X, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { httpClient } from '../../services/httpClient';

interface FileGSTR3BModalProps {
    isOpen: boolean;
    onClose: () => void;
    month: string;
    year: string;
    netTaxPayable: number;
    cashBalance: number;
    onSuccess: () => void;
}

export default function FileGSTR3BModal({
    isOpen,
    onClose,
    month,
    year,
    netTaxPayable,
    cashBalance,
    onSuccess
}: FileGSTR3BModalProps) {
    const [step, setStep] = useState<1 | 2>(1);
    const [otp, setOtp] = useState('');
    const [isFiling, setIsFiling] = useState(false);
    const [isGeneratingChallan, setIsGeneratingChallan] = useState(false);
    const [error, setError] = useState<string | null>(null);
    // Track local cash balance to instantly update UI after challan generation
    const [localCashBalance, setLocalCashBalance] = useState(cashBalance);

    // Sync local cash balance if props change (e.g. initial load)
    React.useEffect(() => {
        setLocalCashBalance(cashBalance);
    }, [cashBalance]);

    if (!isOpen) return null;

    const remainingToPay = Math.max(0, netTaxPayable - localCashBalance);

    const handleGenerateChallan = async () => {
        setIsGeneratingChallan(true);
        setError(null);
        try {
            const res: any = await httpClient.post('/api/gst/reconciliation/generate_pmt06_challan/', {
                amount: remainingToPay
            });
            if (res.success) {
                setLocalCashBalance(res.new_balance);
            } else {
                setError(res.message || 'Failed to generate challan');
            }
        } catch (err) {
            setError('Error generating PMT-06 Challan via Banking Sandbox API');
        } finally {
            setIsGeneratingChallan(false);
        }
    };

    const handleFile = async () => {
        if (!otp || otp.length !== 6) {
            setError('Please enter a valid 6-digit OTP.');
            return;
        }

        setIsFiling(true);
        setError(null);

        try {
            const res: any = await httpClient.post('/api/gst/reconciliation/file_gstr3b_sandbox/', {
                month,
                year,
                otp,
                paid_via_cash: Math.min(netTaxPayable, localCashBalance)
            });

            if (res.success) {
                onSuccess();
            } else {
                setError(res.message || 'Filing failed.');
            }
        } catch (err: any) {
            setError('An error occurred while connecting to the GST Sandbox API.');
        } finally {
            setIsFiling(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl overflow-hidden">
                <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-indigo-50/50">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">File GSTR-3B Return</h2>
                        <p className="text-sm text-gray-500 mt-1">Period: {month} {year}</p>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6">
                    {step === 1 ? (
                        <div className="space-y-6">
                            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                                <div className="flex justify-between items-center pb-3 border-b border-gray-200">
                                    <span className="text-gray-600 font-medium">Net Tax Payable:</span>
                                    <span className="text-gray-900 font-bold text-lg">₹{netTaxPayable.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-gray-500">Available Cash Ledger Balance:</span>
                                    <span className="text-green-600 font-medium">₹{localCashBalance.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm pb-1 border-b border-gray-200">
                                    <span className="text-gray-500">Cash to be offset:</span>
                                    <span className="text-red-500 font-medium">- ₹{Math.min(netTaxPayable, localCashBalance).toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-center pt-2">
                                    <span className="text-gray-900 font-medium">Remaining Shortfall:</span>
                                    <span className={`font-bold ${remainingToPay > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                        ₹{remainingToPay.toFixed(2)}
                                    </span>
                                </div>
                            </div>
                            
                            {error && step === 1 && (
                                <div className="text-sm text-red-500 bg-red-50 p-3 rounded-lg border border-red-100">
                                    {error}
                                </div>
                            )}

                            {remainingToPay > 0 ? (
                                <div className="bg-red-50 border border-red-100 rounded-lg p-4 flex gap-3">
                                    <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="text-sm font-semibold text-red-800">Insufficient Funds</h4>
                                        <p className="text-sm text-red-700 mt-1">
                                            You do not have enough cash in your electronic ledger to offset this liability. 
                                            You must generate a PMT-06 challan and pay the balance before filing.
                                        </p>
                                        <button 
                                            onClick={handleGenerateChallan}
                                            disabled={isGeneratingChallan}
                                            className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70"
                                        >
                                            {isGeneratingChallan ? (
                                                <><RefreshCw className="w-4 h-4 animate-spin" /> Processing Payment...</>
                                            ) : (
                                                'GENERATE PMT-06 CHALLAN'
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-green-50 border border-green-100 rounded-lg p-4 flex gap-3">
                                    <CheckCircle className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="text-sm font-semibold text-green-800">Ready to File</h4>
                                        <p className="text-sm text-green-700 mt-1">
                                            You have sufficient funds to offset the liability. You may proceed to file the return.
                                        </p>
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-end pt-4">
                                <button
                                    onClick={() => setStep(2)}
                                    disabled={remainingToPay > 0}
                                    className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
                                        remainingToPay > 0 
                                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                    }`}
                                >
                                    Proceed to Authenticate
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="text-center">
                                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <AlertCircle className="w-6 h-6 text-indigo-600" />
                                </div>
                                <h3 className="text-lg font-bold text-gray-900">Authenticate via EVC</h3>
                                <p className="text-sm text-gray-500 mt-2">
                                    An OTP has been sent to the registered mobile number ending in ****1234.
                                </p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Enter 6-Digit OTP</label>
                                <input
                                    type="text"
                                    maxLength={6}
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                                    placeholder="Enter OTP (e.g. 123456)"
                                    className="w-full px-4 py-3 text-center tracking-widest text-lg font-bold border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                                {error && (
                                    <p className="text-sm text-red-500 mt-2 text-center">{error}</p>
                                )}
                            </div>

                            <div className="flex justify-between items-center pt-4">
                                <button
                                    onClick={() => setStep(1)}
                                    className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900"
                                >
                                    Back
                                </button>
                                <button
                                    onClick={handleFile}
                                    disabled={isFiling}
                                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-70"
                                >
                                    {isFiling ? (
                                        <>
                                            <RefreshCw className="w-4 h-4 animate-spin" />
                                            Filing to GSTN...
                                        </>
                                    ) : (
                                        'File GSTR-3B'
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
