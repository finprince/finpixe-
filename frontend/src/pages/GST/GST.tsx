import finpixeLogo from '../../assets/branding/logo';
import React, { useState, useEffect } from 'react';
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
        { id: 'GSTR2', label: 'GSTR2 - Inward Supplies' },
        { id: 'GSTR2B_RECO', label: 'GSTR-2B Reconciliation' },
        { id: 'GSTR3B', label: 'GSTR3B - Summary Return' },
        { id: 'LATE_FEES', label: '⚠ Late Fees & Notices' }
    ];

    const availableTabs = isSuperuser
        ? allTabs
        : allTabs.filter(tab => hasTabAccess('GST', tab.id));

    const [activeTab, setActiveTabState] = useState(() => {
        if (navParams?.tab && availableTabs.find(t => t.id === navParams.tab)) {
            savedGstTab = navParams.tab;
            return navParams.tab;
        }
        if (savedGstTab && availableTabs.find(t => t.id === savedGstTab)) {
            return savedGstTab;
        }
        return availableTabs.length > 0 ? availableTabs[0].id : '';
    });

    const setActiveTab = (tabId: string) => {
        savedGstTab = tabId;
        setActiveTabState(tabId);
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
        if (navParams?.tab && availableTabs.find(t => t.id === navParams.tab)) {
            setActiveTab(navParams.tab);
        }
    }, [navParams]);

    useEffect(() => {
        if (availableTabs.length > 0 && !availableTabs.find(t => t.id === activeTab)) {
            const defaultTab = availableTabs[0].id;
            setActiveTab(defaultTab);
        }
    }, [availableTabs, activeTab]);

    return (
        <UniversalWorkspaceLayout
            title="GST & Financial Intelligence Center"
            subtitle="Comprehensive GST filing, GSTR-2B automated reconciliation, and tax analytics."
            badgeText="GST INTELLIGENCE"
            inspectorState={inspectorState}
            onCloseInspector={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
        >
            <div className="flex flex-col gap-6">



            {/* Main Tabs */}
            <div className="erp-tab-container">
                {availableTabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`erp-tab ${activeTab === tab.id ? 'active' : ''}`}
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
                    <GSTR2Reconciliation onNavigate={onNavigate} setViewVoucherData={setViewVoucherData} />
                )}

                {activeTab === 'GSTR3B' && (
                    <GSTR3BPreview />
                )}

                {activeTab === 'LATE_FEES' && (
                    <LateFeeEngine />
                )}
            </div>
            </div>
        </UniversalWorkspaceLayout>
    );
}
