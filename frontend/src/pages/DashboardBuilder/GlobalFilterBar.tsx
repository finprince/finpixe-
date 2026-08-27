import React, { useState } from 'react';
import { Filter, X, Calendar, User, Users, RotateCcw, ChevronDown, Check, Search } from 'lucide-react';
import { useDashboardStore } from '../../store/dashboardStore';

interface GlobalFilterBarProps {
    customers: string[];
    vendors: string[];
}

const GlobalFilterBar: React.FC<GlobalFilterBarProps> = ({ customers, vendors }) => {
    const { globalFilters, setGlobalFilters } = useDashboardStore();
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

    const handleClear = () => {
        setGlobalFilters({
            dateRange: null,
            customer: null,
            vendor: null,
            searchQuery: null,
        });
    };

    const activeFiltersCount = [
        globalFilters.dateRange,
        globalFilters.customer,
        globalFilters.vendor,
        globalFilters.searchQuery
    ].filter(Boolean).length;

    const toggleDropdown = (id: string) => {
        setActiveDropdown(activeDropdown === id ? null : id);
    };

    const selectFilter = (id: string, value: string | null) => {
        setGlobalFilters({ [id]: value });
        setActiveDropdown(null);
    };

    const slicers = [
        { id: 'dateRange', label: 'All Dates', icon: Calendar, options: ['This Month', 'Last Month', 'This Quarter', 'This Year'] },
        { id: 'customer', label: 'All Customers', icon: User, options: customers },
        { id: 'vendor', label: 'All Vendors', icon: Users, options: vendors }
    ];

    return (
        <div className="bg-white border-b border-slate-200 px-6 py-2.5 flex items-center justify-between z-[60] shadow-sm">
            <div className="flex items-center gap-4 flex-1">
                <div className="flex items-center gap-2.5 px-3 py-1 bg-slate-100 rounded-lg">
                    <Filter size={12} className="text-slate-500" strokeWidth={2.5} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-800">Global Filters</span>
                    {activeFiltersCount > 0 && (
                        <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.5 rounded-full font-black animate-in zoom-in duration-300">
                            {activeFiltersCount}
                        </span>
                    )}
                </div>

                {/* Text Box Search Filter Slicer */}
                <div className="relative min-w-[240px] flex-1 max-w-sm">
                    <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" strokeWidth={2.5} />
                    <input
                        type="text"
                        placeholder="Text Box Filter (e.g. Bharat, Infosys, Dell)..."
                        value={globalFilters.searchQuery || ''}
                        onChange={(e) => setGlobalFilters({ searchQuery: e.target.value || null })}
                        className={`w-full pl-9 pr-8 py-1.5 bg-slate-50 border-2 rounded-xl text-xs font-bold text-slate-700 outline-none transition-all ${globalFilters.searchQuery ? 'border-indigo-500 bg-indigo-50/40 text-indigo-900 shadow-sm' : 'border-slate-100 focus:border-indigo-500'}`}
                    />
                    {globalFilters.searchQuery && (
                        <button
                            onClick={() => setGlobalFilters({ searchQuery: null })}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-700 transition-colors"
                        >
                            <X size={12} strokeWidth={3} />
                        </button>
                    )}
                </div>

                <div className="flex items-center gap-3">
                    {slicers.map(f => (
                        <div key={f.id} className="relative">
                            <button
                                onClick={() => toggleDropdown(f.id)}
                                className={`flex items-center gap-2.5 px-4 py-1.5 rounded-xl text-[11px] font-bold border-2 transition-all ${(globalFilters as any)[f.id]
                                    ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-md shadow-indigo-50'
                                    : 'bg-white border-slate-100 text-slate-500 hover:border-slate-300'
                                    }`}
                            >
                                <f.icon size={12} strokeWidth={2.5} />
                                <span>{(globalFilters as any)[f.id] || f.label}</span>
                                <ChevronDown size={10} strokeWidth={3} className={`opacity-40 transition-transform ${activeDropdown === f.id ? 'rotate-180' : ''}`} />
                            </button>

                            {activeDropdown === f.id && (
                                <div className="absolute top-full left-0 mt-2 w-56 bg-white border border-slate-200 rounded-2xl shadow-2xl py-2 z-[100] animate-in slide-in-from-top-2 duration-200">
                                    <div className="px-4 py-2 border-b border-slate-50 mb-1">
                                        <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Select {f.id}</p>
                                    </div>
                                    <button
                                        onClick={() => selectFilter(f.id, null)}
                                        className="w-full flex items-center justify-between px-4 py-2 text-[11px] font-bold text-slate-600 hover:bg-slate-50"
                                    >
                                        <span>Clear Filter</span>
                                        {!(globalFilters as any)[f.id] && <Check size={12} className="text-indigo-600" />}
                                    </button>
                                    <div className="max-h-60 overflow-y-auto custom-scrollbar">
                                        {f.options.slice(0, 50).map(opt => (
                                            <button
                                                key={opt}
                                                onClick={() => selectFilter(f.id, opt)}
                                                className={`w-full flex items-center justify-between px-4 py-2 text-[11px] font-bold text-left transition-colors ${(globalFilters as any)[f.id] === opt ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'
                                                    }`}
                                            >
                                                <span className="truncate">{opt}</span>
                                                {(globalFilters as any)[f.id] === opt && <Check size={12} />}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {activeFiltersCount > 0 && (
                <button
                    onClick={handleClear}
                    className="flex items-center gap-1.5 px-4 py-1.5 text-[10px] font-black uppercase tracking-widest text-red-600 hover:bg-red-50 rounded-xl transition-all"
                >
                    <RotateCcw size={12} strokeWidth={3} />
                    Reset Filters
                </button>
            )}

            <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 10px; }
      `}</style>
        </div>
    );
};

export default GlobalFilterBar;
