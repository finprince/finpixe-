import React from 'react';
import { Search, Filter, Download, Maximize2, RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface WorkspaceToolbarProps {
  onSearchChange?: (query: string) => void;
  onFilterClick?: () => void;
  onExportExcel?: () => void;
  onExportPdf?: () => void;
  onRefresh?: () => void;
  searchPlaceholder?: string;
  children?: React.ReactNode;
}

export const WorkspaceToolbar: React.FC<WorkspaceToolbarProps> = ({
  onSearchChange,
  onFilterClick,
  onExportExcel,
  onExportPdf,
  onRefresh,
  searchPlaceholder = 'Search records...',
  children
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-white rounded-2xl border border-slate-200 shadow-xs mb-6">
      {/* Left Search Input */}
      <div className="flex items-center gap-3 flex-1 min-w-[240px]">
        {onSearchChange && (
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={searchPlaceholder}
              onChange={e => onSearchChange(e.target.value)}
              className="w-full h-10 pl-10 pr-4 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#F97316] focus:ring-2 focus:ring-[#F97316]/20 transition-all"
            />
          </div>
        )}
        {children}
      </div>

      {/* Right Action Buttons */}
      <div className="flex items-center gap-2 shrink-0">
        {onFilterClick && (
          <Button variant="secondary" size="sm" onClick={onFilterClick} className="gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <span>Filters</span>
          </Button>
        )}

        {onRefresh && (
          <Button variant="ghost" size="sm" onClick={onRefresh} className="p-2.5">
            <RefreshCw className="w-4 h-4 text-slate-500" />
          </Button>
        )}

        {(onExportExcel || onExportPdf) && (
          <div className="flex items-center gap-1.5 border-l border-slate-200 pl-2">
            {onExportExcel && (
              <Button variant="ghost" size="sm" onClick={onExportExcel} className="gap-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                <Download className="w-3.5 h-3.5" />
                <span>Excel</span>
              </Button>
            )}
            {onExportPdf && (
              <Button variant="ghost" size="sm" onClick={onExportPdf} className="gap-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                <Download className="w-3.5 h-3.5" />
                <span>PDF</span>
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
