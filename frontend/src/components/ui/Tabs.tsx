import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}) => {
  return (
    <div className={`erp-tab-container ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`erp-tab ${isActive ? 'active' : ''}`}
          >
            <span>{tab.label}</span>
            {typeof tab.count === 'number' && (
              <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${isActive ? 'bg-indigo-100 text-[#4F46E5]' : 'bg-slate-100 text-slate-500'}`}>
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;
