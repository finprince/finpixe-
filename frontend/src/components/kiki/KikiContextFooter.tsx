import React from 'react';
import { Building2, Share2, Calendar, ShieldCheck, Zap } from 'lucide-react';

interface KikiContextFooterProps {
  company?: string;
  branch?: string;
  financialYear?: string;
  currentModule?: string;
}

export const KikiContextFooter: React.FC<KikiContextFooterProps> = ({
  company = "Active Company",
  branch = "Main Branch",
  financialYear = "FY 2026-27",
  currentModule = "Accounting ERP"
}) => {
  return (
    <div className="h-7 px-4 bg-[#F8FAFC] dark:bg-slate-900 border-t border-[#E5E7EB] dark:border-slate-800 text-[10px] text-slate-500 flex items-center justify-between font-mono shrink-0 select-none">
      <div className="flex items-center gap-3 overflow-x-auto whitespace-nowrap scrollbar-none">
        <span className="flex items-center gap-1 font-medium text-slate-700 dark:text-slate-300">
          <Building2 className="w-3 h-3 text-[#FF8A00]" />
          <span>{company}</span>
        </span>
        <span className="text-slate-300 dark:text-slate-700">•</span>
        <span className="flex items-center gap-1">
          <Share2 className="w-3 h-3 text-slate-400" />
          <span>{branch}</span>
        </span>
        <span className="text-slate-300 dark:text-slate-700">•</span>
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3 text-slate-400" />
          <span>{financialYear}</span>
        </span>
        <span className="text-slate-300 dark:text-slate-700">•</span>
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-500" />
          <span>{currentModule}</span>
        </span>
      </div>

      <div className="flex items-center gap-1.5 text-slate-400 font-sans text-[10px]">
        <Zap className="w-3 h-3 text-[#FF8A00]" />
        <span>Kiki AI Command Center</span>
      </div>
    </div>
  );
};
