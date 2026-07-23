import React from 'react';
import type { Page } from '../types';
import Icon from './Icon';
import { usePermissions } from '../hooks/usePermissions';
import { useSubscriptionUsage } from '../hooks/useSubscriptionUsage';

interface SidebarProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  onLogout: () => void;
  companyName: string;
  isOpen?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate, onLogout, companyName, isOpen = true }) => {
  const { hasPageAccess } = usePermissions();
  const { subscriptionUsage } = useSubscriptionUsage();

  const allNavItems: { name: Page; icon: string; label?: string }[] = [
    { name: 'Dashboard', icon: 'dashboard' },
    { name: 'Masters', icon: 'ledger', label: 'Accounting Master' },
    { name: 'Inventory', icon: 'inventory' },
    { name: 'Vouchers', icon: 'vouchers' },
    { name: 'Vendor Portal', icon: 'vendor-portal' },
    { name: 'Customer Portal', icon: 'customer-portal' },
    //{ name: 'Payroll', icon: 'payroll' }, // Temporarily hidden
    { name: 'Service', icon: 'service' },
    { name: 'GST', icon: 'gst' },
    { name: 'Reports', icon: 'reports' },
    { name: 'Users & Roles', icon: 'users' },
    { name: 'Settings', icon: 'settings' },
  ];

  const displayItems = allNavItems.filter(item => hasPageAccess(item.name));

  const usagePercent = Math.min(
    100,
    ((subscriptionUsage?.used || 0) / (subscriptionUsage?.limit as number || 1)) * 100
  );
  const usageDisplay =
    subscriptionUsage?.limit === 'Unlimited'
      ? '∞'
      : `${Math.round(usagePercent)}%`;

  return (
    <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col h-full transition-all duration-300 erp-sidebar w-[220px] ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      {/* ── Brand / Profile Section ──────────────────────────── */}
      <div className="p-4 pb-3">
        <div className="flex items-center gap-2.5">
          {/* Company Avatar */}
          <div
            className="flex items-center justify-center w-8 h-8 text-white rounded-lg shrink-0 bg-[#F97316] shadow-md shadow-orange-500/20"
          >
            <span className="text-sm font-bold">
              {companyName?.charAt(0).toUpperCase() || 'A'}
            </span>
          </div>

          {/* Company Name + Plan */}
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-bold truncate tracking-tight text-slate-900 dark:text-white">
              {companyName || 'Admin User'}
            </span>
            <span className="text-[10px] font-semibold truncate mt-0.5 text-slate-500 dark:text-slate-400">
              {subscriptionUsage?.plan || 'Enterprise Plan'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Navigation Links ────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {displayItems.map((item, index) => {
          const isActive = currentPage === item.name;

          // Define section headers
          let sectionHeader = null;
          if (index === 0) sectionHeader = 'Core Workspace';
          else if (item.name === 'Vendor Portal') sectionHeader = 'Portals & Operations';
          else if (item.name === 'GST') sectionHeader = 'Compliance & Audit';
          else if (item.name === 'Users & Roles') sectionHeader = 'Administration';

          return (
            <React.Fragment key={item.name}>
              {sectionHeader && (
                <div className="erp-nav-section-label">
                  {sectionHeader}
                </div>
              )}
              <button
                onClick={() => onNavigate(item.name)}
                className={`erp-nav-item ${isActive ? 'active' : ''}`}
              >
              <div className="erp-nav-icon">
                  <Icon name={item.icon as any} className="w-4 h-4" />
                </div>
                <span className="flex-1 text-left">{item.label || item.name}</span>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-[#F97316]" />
                )}
              </button>
            </React.Fragment>
          );
        })}
      </nav>

      {/* ── Footer: Storage + Logout ─────────────────────────── */}
      <div className="px-4 pb-6 pt-2 border-t border-slate-100">
        {/* Storage Box */}
        <div className="erp-storage-card mb-3">
          <div className="flex items-center justify-between mb-2.5">
            <span className="erp-kpi-label">AI Usage</span>
            <span className="erp-badge erp-badge-primary text-[10px]">
              {usageDisplay}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 bg-orange-50 dark:bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#F97316] rounded-full transition-all duration-500"
              style={{ width: `${usagePercent}%` }}
            />
          </div>

          <div className="mt-2 flex justify-between text-[11px] text-slate-400 font-medium">
            <span>Used</span>
            <span>
              {subscriptionUsage?.used} / {subscriptionUsage?.limit}
            </span>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={onLogout}
          className="erp-nav-item hover:text-rose-600 hover:bg-rose-50"
        >
          <div className="erp-nav-icon">
            <Icon name="logout" className="w-4 h-4" />
          </div>
          <span>Log Out</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
