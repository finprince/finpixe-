import React, { useState, useRef, useEffect, useMemo } from 'react';
import Icon from './Icon';
import { CommandPalette } from './ui/CommandPalette';
import { useCommandPalette } from '../hooks/useCommandPalette';
import type { CommandAction } from '../types/types';
import { ChevronUp } from 'lucide-react';

interface MasterHeaderProps {
  title: string;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  adminName: string;
  onNavigate?: (page: string, params?: any) => void;
  onLogout?: () => void;
  onCollapseHeader?: () => void;
}

const MasterHeader: React.FC<MasterHeaderProps> = ({
  title,
  isSidebarOpen,
  toggleSidebar,
  adminName,
  onNavigate,
  onLogout,
  onCollapseHeader
}) => {
  const { isOpen, open, close } = useCommandPalette();
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const toolsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
        setIsToolsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const actions: CommandAction[] = useMemo(() => {
    const nav = (page: string, params?: any) => () => {
      if (onNavigate) onNavigate(page, params);
      close();
    };
    return [
      // Primary Module Navigation
      { id: 'nav-dash', title: 'Dashboard - Executive Command Cockpit', category: 'Navigation', perform: nav('Dashboard') },
      { id: 'nav-dash-builder', title: 'Dashboard Builder - Customize Cockpit Widgets', category: 'Dashboard', perform: nav('Dashboard Builder') },
      
      { id: 'nav-masters', title: 'Masters - Accounting Master Studio', category: 'Navigation', perform: nav('Masters') },
      { id: 'nav-masters-ledgers', title: 'Masters > Ledgers & Ledger Groups Configuration', category: 'Masters', perform: nav('Masters', { tab: 'Ledgers' }) },
      { id: 'nav-masters-vouchers', title: 'Masters > Voucher Types numbering series config', category: 'Masters', perform: nav('Masters', { tab: 'Vouchers' }) },

      { id: 'nav-vouchers', title: 'Vouchers - Smart Voucher Focus Studio', category: 'Navigation', perform: nav('Vouchers') },
      { id: 'nav-vouchers-sales', title: 'Vouchers > Create Sales Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Sales' }) },
      { id: 'nav-vouchers-purchase', title: 'Vouchers > Create Purchase Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Purchase' }) },
      { id: 'nav-vouchers-payment', title: 'Vouchers > Create Payment Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Payment' }) },
      { id: 'nav-vouchers-receipt', title: 'Vouchers > Create Receipt Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Receipt' }) },
      { id: 'nav-vouchers-contra', title: 'Vouchers > Create Contra Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Contra' }) },
      { id: 'nav-vouchers-journal', title: 'Vouchers > Create Journal Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Journal' }) },
      { id: 'nav-vouchers-expenses', title: 'Vouchers > Create Expenses Voucher entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Expenses' }) },
      { id: 'nav-vouchers-credit-note', title: 'Vouchers > Create Credit Note entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Credit Note' }) },
      { id: 'nav-vouchers-debit-note', title: 'Vouchers > Create Debit Note entry', category: 'Vouchers', perform: nav('Vouchers', { action: 'create', type: 'Debit Note' }) },

      { id: 'nav-inventory', title: 'Inventory - Stock Intelligence Center', category: 'Navigation', perform: nav('Inventory') },
      { id: 'nav-inventory-items', title: 'Inventory > Stock Items database', category: 'Inventory', perform: nav('Inventory', { tab: 'Master', subTab: 'Inventory Items' }) },
      { id: 'nav-inventory-category', title: 'Inventory > Category Hierarchies list', category: 'Inventory', perform: nav('Inventory', { tab: 'Master', subTab: 'Category' }) },
      { id: 'nav-inventory-location', title: 'Inventory > Location & Godown details', category: 'Inventory', perform: nav('Inventory', { tab: 'Master', subTab: 'Location' }) },
      { id: 'nav-inventory-movement', title: 'Inventory > Stock Movement logs', category: 'Inventory', perform: nav('Inventory', { tab: 'Operations', subTab: 'Stock Movement' }) },

      { id: 'nav-gst', title: 'GST - GST & Financial Intelligence Center', category: 'Navigation', perform: nav('GST') },
      { id: 'nav-gst-gstr1', title: 'GST > GSTR1 Outward Supplies return preview', category: 'GST', perform: nav('GST', { tab: 'GSTR1' }) },
      { id: 'nav-gst-gstr2', title: 'GST > GSTR2 Inward Supplies return view', category: 'GST', perform: nav('GST', { tab: 'GSTR2' }) },
      { id: 'nav-gst-reco', title: 'GST > GSTR-2B Automated Reconciliation dashboard', category: 'GST', perform: nav('GST', { tab: 'GSTR2B_RECO' }) },
      { id: 'nav-gst-gstr3b', title: 'GST > GSTR3B Summary Tax Return preview', category: 'GST', perform: nav('GST', { tab: 'GSTR3B' }) },
      { id: 'nav-gst-latefees', title: 'GST > Late Fees & Notices warning engine', category: 'GST', perform: nav('GST', { tab: 'LATE_FEES' }) },

      { id: 'nav-reports', title: 'Reports - Financial Reports Command Center', category: 'Navigation', perform: nav('Reports') },
      { id: 'nav-reports-daybook', title: 'Reports > Day Book transaction log', category: 'Reports', perform: nav('Reports', { reportType: 'DayBook' }) },
      { id: 'nav-reports-ledger', title: 'Reports > Ledger Report statements', category: 'Reports', perform: nav('Reports', { reportType: 'LedgerReport' }) },
      { id: 'nav-reports-trial', title: 'Reports > Trial Balance financial statement', category: 'Reports', perform: nav('Reports', { reportType: 'TrialBalance' }) },
      { id: 'nav-reports-balance', title: 'Reports > Balance Sheet asset liability overview', category: 'Reports', perform: nav('Reports', { reportType: 'BalanceSheet' }) },
      { id: 'nav-reports-stock', title: 'Reports > Stock Summary valuation report', category: 'Reports', perform: nav('Reports', { reportType: 'StockSummary' }) },
      { id: 'nav-reports-gst', title: 'Reports > GST reports summaries', category: 'Reports', perform: nav('Reports', { reportType: 'GSTReports' }) },
      { id: 'nav-reports-ai', title: 'Reports > AI Report anomaly detection stream', category: 'Reports', perform: nav('Reports', { reportType: 'AIReport' }) },

      { id: 'nav-settings', title: 'Settings - System Profile & Preferences', category: 'Navigation', perform: nav('Settings') },
      { id: 'nav-settings-profile', title: 'Settings > Company Profile meta configuration', category: 'Settings', perform: nav('Settings', { tab: 'Company Profile' }) },
      { id: 'nav-settings-tax', title: 'Settings > Tax Details (GSTIN, PAN)', category: 'Settings', perform: nav('Settings', { tab: 'Tax Settings' }) },
      { id: 'nav-settings-regional', title: 'Settings > Regional currency and timezone', category: 'Settings', perform: nav('Settings', { tab: 'Regional Settings' }) },
      { id: 'nav-settings-subscription', title: 'Settings > Subscription plan upgrade details', category: 'Settings', perform: nav('Settings', { tab: 'Subscription' }) },

      { id: 'nav-users', title: 'Users & Roles - Access Control RBAC Dashboard', category: 'Navigation', perform: nav('Users & Roles') },
      { id: 'nav-users-list', title: 'Users & Roles > User Management creation list', category: 'Users & Roles', perform: nav('Users & Roles', { tab: 'users' }) },
      { id: 'nav-users-permissions', title: 'Users & Roles > Roles & Permissions config', category: 'Users & Roles', perform: nav('Users & Roles', { tab: 'roles' }) },

      { id: 'nav-vendor', title: 'Vendor Portal - Multi Vendor Dashboard', category: 'Navigation', perform: nav('Vendor Portal') },
      { id: 'nav-vendor-create', title: 'Vendor Portal > Vendor Profile Creation wizard', category: 'Vendor Portal', perform: nav('Vendor Portal', { tab: 'Vendor Creation' }) },
      { id: 'nav-vendor-bills', title: 'Vendor Portal > Pending Bills payments list', category: 'Vendor Portal', perform: nav('Vendor Portal', { tab: 'Pending Bills' }) },
      { id: 'nav-vendor-tds', title: 'Vendor Portal > TDS rules configuration', category: 'Vendor Portal', perform: nav('Vendor Portal', { tab: 'TDS rules' }) },

      { id: 'nav-customer', title: 'Customer Portal - Sales aging intelligence hub', category: 'Navigation', perform: nav('Customer Portal') },
      { id: 'nav-customer-categories', title: 'Customer Portal > Sales Category configurations', category: 'Customer Portal', perform: nav('Customer Portal', { tab: 'Category' }) },
      { id: 'nav-customer-orders', title: 'Customer Portal > Sales Quotation & Orders tracking', category: 'Customer Portal', perform: nav('Customer Portal', { tab: 'Sales Quotation & Order' }) },
      { id: 'nav-customer-create', title: 'Customer Portal > Customer Profile Creation wizard', category: 'Customer Portal', perform: nav('Customer Portal', { tab: 'Customer' }) },
      { id: 'nav-customer-contracts', title: 'Customer Portal > Long-term Contract templates', category: 'Customer Portal', perform: nav('Customer Portal', { tab: 'Long-term Contracts' }) },

      { id: 'nav-service', title: 'Service - Services & SAC Management Center', category: 'Navigation', perform: nav('Service') },
      { id: 'nav-service-group', title: 'Service > Service Group hierarchies hierarchy', category: 'Service', perform: nav('Service', { tab: 'service-group' }) },
      { id: 'nav-service-list', title: 'Service > Service List database catalog', category: 'Service', perform: nav('Service', { tab: 'service-list' }) },

      { id: 'nav-payroll', title: 'Payroll - Employee Salary & Slip center', category: 'Navigation', perform: nav('Payroll') },
      { id: 'nav-pending', title: 'Pending Purchases - Scanned bills review queue', category: 'Navigation', perform: nav('Pending Purchases') },
    ];
  }, [onNavigate, close]);

  return (
    <>
      <header className="sticky top-0 z-30 relative backdrop-blur-md flex items-center justify-between px-8 py-3.5 bg-white/90 border-b border-slate-200 shadow-xs">
        {/* Left Toggle & Context Title */}
        <div className="flex items-center gap-4">
          <button
            onClick={toggleSidebar}
            className="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-600 transition-all active:scale-95 shrink-0"
            title={isSidebarOpen ? 'Hide Sidebar' : 'Show Sidebar'}
          >
            <Icon name="menu" className="w-5 h-5" />
          </button>

          <div className="flex flex-col">
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight leading-tight">
              {title}
            </h1>
            <span className="text-[11px] font-semibold text-slate-500">
              {adminName || 'Finpixe AI Operating System'}
            </span>
          </div>
        </div>

        {/* Center Global Command Palette Trigger Button */}
        <div className="flex-1 max-w-md mx-8">
          <button
            onClick={open}
            className="w-full flex items-center justify-between px-4 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-medium text-slate-500 transition-all shadow-xs group"
          >
            <div className="flex items-center gap-2.5">
              <Icon name="search" className="w-4 h-4 text-slate-400 group-hover:text-[#4F46E5] transition-colors" />
              <span>Search commands, vouchers, reports (Ctrl+K)...</span>
            </div>
            <kbd className="px-2 py-0.5 text-[10px] font-mono font-bold bg-white text-slate-600 rounded border border-slate-200 shadow-2xs">
              Ctrl+K
            </kbd>
          </button>
        </div>

        {/* Right Action Tools & Profile Dropdown */}
        <div className="flex items-center gap-3">
          {/* Tools Menu */}
          <div ref={toolsRef} className="relative">
            <button
              onClick={() => setIsToolsOpen(prev => !prev)}
              className="flex items-center gap-2 px-3.5 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 transition-all"
            >
              <Icon name="settings" className="w-4 h-4 text-[#4F46E5]" />
              <span>Tools</span>
              <Icon name="chevron-down" className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isToolsOpen ? 'rotate-180' : ''}`} />
            </button>

            {isToolsOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-2xl shadow-xl py-2 z-50 flex flex-col animate-in fade-in zoom-in-95 duration-150">
                <button
                  onClick={() => {
                    setIsToolsOpen(false);
                    if ((window as any).toggleGlobalCalculator) (window as any).toggleGlobalCalculator(true);
                  }}
                  className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-indigo-50 hover:text-[#4F46E5] transition-colors"
                >
                  <Icon name="calculator" className="w-4 h-4" />
                  <span>Calculator</span>
                </button>
                <button
                  onClick={() => {
                    setIsToolsOpen(false);
                    if ((window as any).toggleGlobalCalendar) (window as any).toggleGlobalCalendar(true);
                  }}
                  className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-indigo-50 hover:text-[#4F46E5] transition-colors"
                >
                  <Icon name="calendar" className="w-4 h-4" />
                  <span>Reminders</span>
                </button>
                <button
                  onClick={() => {
                    setIsToolsOpen(false);
                    if ((window as any).toggleGlobalNotes) (window as any).toggleGlobalNotes(true);
                  }}
                  className="flex items-center gap-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-indigo-50 hover:text-[#4F46E5] transition-colors"
                >
                  <Icon name="file-text" className="w-4 h-4" />
                  <span>Notes</span>
                </button>
              </div>
            )}
          </div>

          {/* User Avatar Card / Logout */}
          {onLogout && (
            <button
              onClick={onLogout}
              className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-rose-50 transition-colors"
              title="Sign Out"
            >
              <Icon name="logout" className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Collapse Header Button (Middle Tab) */}
        {onCollapseHeader && (
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full z-40">
            <button
              onClick={onCollapseHeader}
              className="w-10 h-6 bg-white hover:bg-slate-50 border border-t-0 border-slate-200 rounded-b-xl shadow-xs flex items-center justify-center text-slate-400 hover:text-indigo-600 transition-all active:scale-95"
              title="Hide Header"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
          </div>
        )}
      </header>

      {/* Command Palette Modal */}
      <CommandPalette isOpen={isOpen} onClose={close} actions={actions} />
    </>
  );
};

export default MasterHeader;
