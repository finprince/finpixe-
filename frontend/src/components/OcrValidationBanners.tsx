import React from 'react';

interface OcrValidationBannersProps {
    record: any;
    onGstResolution: (choice: 'CORRECTED' | 'SUPPLIER_VALUES_ACCEPTED') => void;
    onResetGstResolution: () => void;
    onCreateVendor: () => void;
}

export const OcrValidationBanners: React.FC<OcrValidationBannersProps> = ({
    record,
    onCreateVendor
}) => {
    if (!record) return null;

    const data = record.extracted_data || {};
    const sections = data.sections || {};
    const vendorStatus = record.vendor_status || '';
    const vendorName = record.vendor_name || sections.supplier_details?.vendor_name || data.vendor_name || '';

    return (
        <div className="space-y-4 mb-6">
            {/* Vendor Status Headers */}
            {['EXISTS', 'FOUND', 'MATCHED'].includes(vendorStatus) ? (
                <div className="px-6 py-4 bg-emerald-50 border border-emerald-100 rounded-xl flex items-center justify-between shadow-xs">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center text-xl">✅</div>
                        <div className="text-left">
                            <h4 className="font-bold text-emerald-900 text-sm uppercase tracking-wider">Matched</h4>
                            <p className="text-[10px] text-emerald-700 italic">This vendor exists in your master list: {vendorName}</p>
                        </div>
                    </div>
                </div>
            ) : ['NEW', 'MISSING'].includes(vendorStatus) ? (
                <div className="px-6 py-4 bg-indigo-50 border border-indigo-100 rounded-xl flex items-center justify-between shadow-xs">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-xl">⚠️</div>
                        <div className="text-left">
                            <h4 className="font-bold text-indigo-900 text-sm uppercase tracking-wider">Create Vendor</h4>
                            <p className="text-[10px] text-indigo-700 italic">This vendor was not found. Please create it to continue.</p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onCreateVendor}
                        className="px-6 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 transition-colors shadow-md cursor-pointer"
                    >
                        Create New Vendor
                    </button>
                </div>
            ) : (
                <div className="px-6 py-4 bg-blue-50 border border-blue-100 rounded-xl flex items-center gap-3 shadow-xs">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
                    <span className="text-sm font-bold text-blue-700 uppercase">Processing...</span>
                </div>
            )}
        </div>
    );
};
