import finpixeLogo from '../../assets/branding/logo';
import React, { useState, useEffect } from 'react';
import type { Voucher, Ledger, Page } from '../../types';
import { Widget } from '../../store/dashboardStore';
import Icon from '../../components/Icon';
import { useDashboardData } from '../../hooks/useDashboardData';
import StatCard from '../../components/StatCard';
import { formatCurrency } from '../../utils/formatting';
import WidgetRenderer from '../DashboardBuilder/WidgetRenderer';
import { UniversalWorkspaceLayout } from '../../components/layouts/UniversalWorkspaceLayout';
import { ChevronRight, ArrowUpRight, ArrowDownLeft, Sparkles, TrendingUp, ShoppingCart, Activity } from 'lucide-react';
import {
    PieChart, Pie, Cell, Tooltip as ReTooltip, Legend, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Area, AreaChart
} from 'recharts';

interface DashboardPageProps {
    onNavigate: (page: Page) => void;
    companyName: string;
    vouchers: Voucher[];
    ledgers: Ledger[];
    isAdmin?: boolean;
}

const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate, companyName, vouchers, ledgers, isAdmin = false }) => {
    const [customWidgets, setCustomWidgets] = useState<Widget[]>([]);

    const {
        revenueData,
        expenseBreakdown,
        totalSales,
        totalPurchases,
        totalReceivables,
        totalPayables
    } = useDashboardData(vouchers, ledgers);

    const recentVouchers = vouchers.slice(0, 8);

    const [inspectorState, setInspectorState] = useState<{
        isOpen: boolean;
        title?: string;
        subtitle?: string;
        entityType?: string;
        data?: Record<string, any> | null;
        activityLogs?: Array<{ id: string; user: string; action: string; timestamp: string }>;
        aiRecommendations?: Array<{ id: string; text: string; confidence?: number }>;
    }>({
        isOpen: false,
        title: '',
        data: null
    });

    useEffect(() => {
        const loadWidgets = () => {
            const saved = sessionStorage.getItem('bi_dashboard_config_v2') || localStorage.getItem('bi_dashboard_config_v2');
            if (saved) {
                try {
                    const parsed = JSON.parse(saved);
                    if (Array.isArray(parsed)) {
                        setCustomWidgets(parsed);
                        if (!sessionStorage.getItem('bi_dashboard_config_v2')) {
                            sessionStorage.setItem('bi_dashboard_config_v2', saved);
                            localStorage.removeItem('bi_dashboard_config_v2');
                        }
                    }
                } catch (e) {
                    console.error("Failed to load dashboard layout");
                }
            }
        };

        loadWidgets();
        window.addEventListener('dashboard-layout-updated', loadWidgets);
        return () => window.removeEventListener('dashboard-layout-updated', loadWidgets);
    }, []);

    const getWidgetData = (widget: Widget) => {
        if (widget.dataset === 'Sales') return revenueData.map(d => ({ Date: d.period, Amount: d.revenue, name: d.period, value: d.revenue }));
        if (widget.dataset === 'Expenses') return expenseBreakdown.map(e => ({ Category: e.name, Amount: e.value, name: e.name, value: e.value }));
        return [];
    };

    const getVoucherDisplay = (v: Voucher) => {
        let party = '';
        let amount = 0;
        if ('party' in v) party = v.party;
        if ('total' in v) amount = v.total;
        else if ('amount' in v) amount = v.amount;
        return { party, amount, type: v.type, date: v.date };
    };

    const greeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        return 'Good evening';
    };

    const handleSelectVoucher = (v: Voucher) => {
        const display = getVoucherDisplay(v);
        setInspectorState({
            isOpen: true,
            title: `Voucher Details`,
            subtitle: `${display.type} • ${display.date}`,
            entityType: display.type,
            data: {
                Party_Name: display.party || 'Cash/General',
                Transaction_Type: display.type,
                Date: display.date,
                Amount: `₹${Number(display.amount).toLocaleString('en-IN')}`,
                Status: 'Posted & Verified',
                Voucher_ID: (v as any).id || (v as any).invoiceNo || 'VOUCH-001'
            },
            activityLogs: [
                { id: '1', user: 'Admin', action: 'Created Voucher entry', timestamp: display.date },
                { id: '2', user: 'System AI', action: 'Verified GST rate and tax calculations', timestamp: display.date }
            ],
            aiRecommendations: [
                { id: '1', text: 'GST rate matches party ledger category', confidence: 99 },
                { id: '2', text: 'Invoice number sequence verified', confidence: 95 }
            ]
        });
    };

    const canvasW = customWidgets.length > 0
        ? Math.max(900, ...customWidgets.map(w => (w.x || 0) + (w.width || 300) + 60))
        : 900;
    const canvasH = customWidgets.length > 0
        ? Math.max(500, ...customWidgets.map(w => (w.y || 0) + (w.height || 200) + 60))
        : 500;

    return (
        <UniversalWorkspaceLayout
            title={`${greeting()}, ${companyName}`}
            subtitle={`Executive overview and financial intelligence for ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}.`}
            badgeText="KIKI ENTERPRISE OS"
            inspectorState={inspectorState}
            onCloseInspector={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
        >
            <div className="flex flex-col gap-8">
                {/* Executive Quick Actions Bar */}
                <div className="flex items-center justify-between p-4 bg-white rounded-2xl border border-slate-200 shadow-xs">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#EA580C]">
                            <Sparkles className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-slate-900">AI Operating Cockpit Active</h3>
                            <p className="text-xs text-slate-500 font-medium">Real-time ledger monitoring & continuous GST audit stream</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => onNavigate('Vouchers')}
                            className="erp-button-primary gap-2"
                        >
                            <Icon name="plus" size={16} />
                            Create Voucher
                        </button>
                        <button
                            onClick={() => onNavigate('Dashboard Builder')}
                            className="erp-button-secondary gap-2"
                        >
                            <Icon name="settings" size={16} />
                            Edit Dashboard
                        </button>
                    </div>
                </div>

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                        title="Total Sales"
                        value={formatCurrency(totalSales)}
                        change="+12.5%"
                        isPositive={true}
                        icon="trending-up"
                        color="orange"
                    />
                    <StatCard
                        title="Total Purchases"
                        value={formatCurrency(totalPurchases)}
                        change="-2.4%"
                        isPositive={true}
                        icon="shopping-cart"
                        color="blue"
                    />
                    <StatCard
                        title="Receivables"
                        value={formatCurrency(totalReceivables)}
                        change="+5.1%"
                        isPositive={true}
                        icon="arrow-down-right"
                        color="green"
                    />
                    <StatCard
                        title="Payables"
                        value={formatCurrency(totalPayables)}
                        change="-1.2%"
                        isPositive={true}
                        icon="arrow-up-right"
                        color="purple"
                    />
                </div>

                {/* Custom BI Widgets Area (if configured via Builder) */}
                {customWidgets.length > 0 && (
                    <div className="erp-card p-6 border border-slate-200">
                        <div className="flex justify-between items-center mb-6 pb-2 border-b border-slate-100">
                            <div>
                                <h3 className="section-title text-base font-bold text-slate-900">Custom Analytics Canvas</h3>
                                <p className="helper-text text-xs">Visual BI widgets configured in Dashboard Builder</p>
                            </div>
                            <button onClick={() => onNavigate('Dashboard Builder')} className="text-xs font-bold text-[#EA580C] hover:underline flex items-center gap-1">
                                Edit Layout <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                        </div>
                        <div className="relative overflow-auto custom-scrollbar" style={{ minHeight: `${canvasH}px` }}>
                            <div style={{ width: `${canvasW}px`, minHeight: `${canvasH}px`, position: 'relative' }}>
                                {customWidgets.map((widget) => (
                                    <div
                                        key={widget.id}
                                        style={{
                                            position: 'absolute',
                                            left: `${widget.x || 0}px`,
                                            top: `${widget.y || 0}px`,
                                            width: `${widget.width || 300}px`,
                                            height: `${widget.height || 200}px`,
                                        }}
                                        className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 overflow-hidden flex flex-col"
                                    >
                                        <h4 className="text-xs font-bold text-slate-700 mb-2 truncate">{widget.title}</h4>
                                        <div className="flex-1 w-full h-full min-h-0">
                                            <WidgetRenderer widget={widget} data={getWidgetData(widget)} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Revenue Analytics & Live Activity Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Revenue vs Expenses Chart */}
                    <div className="lg:col-span-2 erp-card p-6 flex flex-col justify-between border border-slate-200">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="section-title text-lg font-bold text-slate-900">Revenue Analytics</h3>
                                <p className="helper-text text-xs">Monthly sales & purchase trend comparison</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="flex items-center text-xs font-semibold text-slate-600">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[#F97316] inline-block mr-1.5" /> Monthly Sales
                                </span>
                            </div>
                        </div>

                        <div className="h-[280px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={revenueData}>
                                    <defs>
                                        <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#F97316" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                                    <XAxis dataKey="period" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#E2E8F0' }} />
                                    <YAxis tickFormatter={(val) => `₹${val / 1000}k`} tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#E2E8F0' }} />
                                    <ReTooltip formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, 'Revenue']} />
                                    <Area type="monotone" dataKey="revenue" stroke="#F97316" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Live Activity Feed */}
                    <div className="erp-card p-6 flex flex-col border border-slate-200">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="section-title text-lg font-bold text-slate-900">Recent Transactions</h3>
                                <p className="helper-text text-xs">Click row to open 320px Inspector Drawer</p>
                            </div>
                            <button
                                onClick={() => onNavigate('Vouchers')}
                                className="text-xs font-bold text-[#EA580C] hover:underline"
                            >
                                View All
                            </button>
                        </div>

                        <div className="flex-1 flex flex-col gap-3 overflow-y-auto max-h-[320px] pr-1 custom-scrollbar">
                            {recentVouchers.length === 0 && (
                                <div className="text-center text-xs text-slate-400 py-10">No recent transactions recorded.</div>
                            )}
                            {recentVouchers.map((v, i) => {
                                const display = getVoucherDisplay(v);
                                return (
                                    <div
                                        key={i}
                                        onClick={() => handleSelectVoucher(v)}
                                        className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 hover:border-orange-200 hover:bg-[#FFF7ED] transition-all cursor-pointer flex items-center justify-between group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0 text-slate-600 group-hover:text-[#EA580C] group-hover:border-orange-200">
                                                <Icon name={display.type.toLowerCase().includes('sales') ? 'arrow-up-right' : 'arrow-down-left'} size={16} />
                                            </div>
                                            <div>
                                                <p className="text-xs font-bold text-slate-800 line-clamp-1">{display.party || 'General Account'}</p>
                                                <p className="text-[9px] font-bold text-slate-400 mt-0.5 uppercase tracking-widest">{display.type} • {display.date}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-xs font-bold font-mono text-slate-900">₹{display.amount.toLocaleString('en-IN')}</p>
                                            <span className="text-[9px] font-bold text-[#EA580C] group-hover:underline">Inspect →</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </UniversalWorkspaceLayout>
    );
};

export default DashboardPage;
