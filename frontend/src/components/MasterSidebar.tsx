import React from 'react';
import Icon from './Icon';

export type MasterPage = 'Dashboard' | 'Branches' | 'Reports' | 'Settings';

interface MasterSidebarProps {
  currentPage: MasterPage;
  onNavigate: (page: MasterPage) => void;
  onLogout: () => void;
  adminName: string;
  isOpen?: boolean;
}

const MasterSidebar: React.FC<MasterSidebarProps> = ({ 
  currentPage, 
  onNavigate, 
  onLogout, 
  adminName, 
  isOpen = true 
}) => {
  const masterNavItems: { name: MasterPage; icon: string }[] = [
    { name: 'Dashboard', icon: 'dashboard' },
    { name: 'Branches', icon: 'ledger' },  // GSTIN Level
    { name: 'Reports', icon: 'reports' },
    { name: 'Settings', icon: 'settings' },
  ];

  return (
    <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col h-full transition-all duration-300 erp-sidebar w-[220px] ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      {/* ── Brand / Profile Section ──────────────────────────── */}
      <div className="p-4 pb-3">
        <div className="flex items-center gap-2.5">
          {/* Admin Avatar */}
          <div
            className="flex items-center justify-center w-8 h-8 text-white rounded-lg shrink-0 bg-slate-900 shadow-md"
          >
            <span className="text-sm font-bold">
              {adminName?.charAt(0).toUpperCase() || 'M'}
            </span>
          </div>

          {/* Admin Name + Role */}
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-bold truncate tracking-tight text-slate-900 dark:text-white">
              {adminName || 'Master Admin'}
            </span>
            <span className="text-[10px] font-semibold truncate mt-0.5 text-slate-500 dark:text-slate-400">
              Platform Admin
            </span>
          </div>
        </div>
      </div>

      {/* ── Navigation Links ────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <div className="erp-nav-section-label">Platform Admin</div>
        {masterNavItems.map((item) => {
          const isActive = currentPage === item.name;
          return (
            <button
              key={item.name}
              onClick={() => onNavigate(item.name)}
              className={`erp-nav-item ${isActive ? 'active' : ''}`}
            >
              <div className="erp-nav-icon">
                <Icon name={item.icon as any} className="w-4 h-4" />
              </div>
              <span className="flex-1 text-left">{item.name}</span>
              {isActive && (
                <div className="w-1.5 h-1.5 rounded-full bg-[#F97316]" />
              )}
            </button>
          );
        })}
      </nav>

      {/* ── Footer: Logout ─────────────────────────── */}
      <div className="px-4 pb-6 pt-2 border-t border-slate-100">
        {/* Logout Button */}
        <button
          onClick={onLogout}
          className="erp-nav-item w-full hover:text-rose-600 hover:bg-rose-50"
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

export default MasterSidebar;
