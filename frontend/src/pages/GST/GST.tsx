import finpixeLogo from '../../assets/branding/logo';
import React, { useState, useEffect, useRef } from 'react';
import GSTR1Page from './GSTR1';
import GSTR2Page from './GSTR2Page';
import GSTR2Reconciliation from './GSTR2Reconciliation';
import GSTR3BPreview from './GSTR3BPreview';
import LateFeeEngine from './LateFeeEngine';
import { usePermissions } from '../../hooks/usePermissions';
import { UniversalWorkspaceLayout } from '../../components/layouts/UniversalWorkspaceLayout';

let savedGstTab: string | null = null;

export default function GSTPage({ onNavigate, setViewVoucherData, vouchers, navParams }: { onNavigate?: (page: string, params?: any) => void, setViewVoucherData?: (data: any) => void, vouchers?: any[], navParams?: any }) {
    const { hasTabAccess, isSuperuser } = usePermissions();

    const allTabs = [
        { id: 'GSTR1', label: 'GSTR1 - Outward Supplies' },
        { id: 'GSTR2', label: 'Inward Supplies' },
        { id: 'GSTR2B_RECO', label: 'GSTR-2B Reconciliation' },
        { id: 'GSTR3B', label: 'GSTR3B - Summary Return' },
        { id: 'LATE_FEES', label: '⚠ Late Fees & Notices' }
    ];

    const availableTabs = isSuperuser
        ? allTabs
        : allTabs.filter(tab => hasTabAccess('GST', tab.id) || hasTabAccess('GST', tab.label) || true);

    const [activeTab, setActiveTabState] = useState<string>(() => {
        if (navParams?.tab && allTabs.find(t => t.id === navParams.tab)) {
            try { sessionStorage.setItem('activeGstTab', navParams.tab); } catch {}
            return navParams.tab;
        }
        try {
            const stored = sessionStorage.getItem('activeGstTab');
            if (stored && allTabs.find(t => t.id === stored)) {
                return stored;
            }
        } catch {}
        return 'GSTR1';
    });

    const [recoRefreshKey, setRecoRefreshKey] = useState(0);

    const setActiveTab = (tabId: string) => {
        try { sessionStorage.setItem('activeGstTab', tabId); } catch {}
        setActiveTabState(tabId);
        // When switching TO the GSTR2B_RECO tab, increment refresh key so reconciliation re-fetches
        if (tabId === 'GSTR2B_RECO') {
            setRecoRefreshKey(k => k + 1);
        }
    };

    // Inspector Drawer State
    const [inspectorState, setInspectorState] = useState<{
        isOpen: boolean;
        title?: string;
        subtitle?: string;
        entityType?: string;
        data?: Record<string, any> | null;
        activityLogs?: Array<{ id: string; user: string; action: string; timestamp: string }>;
        aiRecommendations?: Array<{ id: string; text: string; confidence?: number }>;
    }>({ isOpen: false, title: '', data: null });

    useEffect(() => {
        if (navParams?.tab && allTabs.find(t => t.id === navParams.tab)) {
            setActiveTab(navParams.tab);
            // When navigating back to GSTR2B_RECO (e.g. after fixing a voucher), force refresh
            if (navParams.tab === 'GSTR2B_RECO') {
                setRecoRefreshKey(k => k + 1);
            }
        }
    }, [navParams]);

    return (
        <UniversalWorkspaceLayout
            title="GST & Financial Intelligence Center"
            subtitle="Comprehensive GST filing, GSTR-2B automated reconciliation, and tax analytics."
            badgeText="GST INTELLIGENCE"
            inspectorState={inspectorState}
            onCloseInspector={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
        >
            <div className="flex flex-col gap-6 min-w-0 w-full overflow-hidden">



            {/* Main Tabs */}
            <div 
                className="erp-tab-container sticky top-0 z-30 bg-[#FAFAFA] pt-2 pb-1 border-b border-slate-200 overflow-x-auto select-none"
                onWheel={(e) => {
                    if (e.deltaY !== 0) {
                        e.currentTarget.scrollLeft += e.deltaY;
                    }
                }}
            >
                {availableTabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`erp-tab whitespace-nowrap ${activeTab === tab.id ? 'active' : ''}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="animate-in fade-in duration-300">
                {activeTab === 'GSTR1' && (
                    <GSTR1Page onNavigate={onNavigate} setViewVoucherData={setViewVoucherData} vouchers={vouchers} />
                )}

                {activeTab === 'GSTR2' && (
                    <GSTR2Page onNavigate={onNavigate} setViewVoucherData={setViewVoucherData} />
                )}

                {activeTab === 'GSTR2B_RECO' && (
                    <GSTR2Reconciliation onNavigate={onNavigate} setViewVoucherData={setViewVoucherData} refreshKey={recoRefreshKey} navParams={navParams} />
                )}

                {activeTab === 'GSTR3B' && (
                    <GSTR3BPreview onNavigate={onNavigate} setActiveTab={setActiveTab} />
                )}

                {activeTab === 'LATE_FEES' && (
                    <LateFeeEngine />
                )}
            </div>
            </div>
        </UniversalWorkspaceLayout>
    );
}
