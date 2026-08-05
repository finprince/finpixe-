import React from 'react';
import {
  Search,
  Plus,
  Clock,
  Settings,
  Maximize2,
  Minimize,
  X,
  Zap,
  Building2
} from 'lucide-react';
import kikiLogo from '../../assets/kiki-agent-orange.png';

interface KikiHeaderProps {
  onToggleHistory: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onClose: () => void;
  onNewChat?: () => void;
  onSearchClick?: () => void;
}

export const KikiHeader: React.FC<KikiHeaderProps> = ({
  onToggleHistory,
  isExpanded,
  onToggleExpand,
  onClose,
  onNewChat,
  onSearchClick
}) => {
  return (
    <div className="flex flex-col border-b border-[#E5E7EB] dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 rounded-t-2xl shrink-0 select-none">
      {/* Primary Header Row */}
      <div className="h-14 px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Exact Kiki Fox Logo */}
          <div className="relative w-8 h-8 rounded-xl overflow-hidden bg-orange-50/80 border border-orange-200/60 p-0.5 shrink-0 shadow-2xs">
            <img src={kikiLogo} alt="Kiki AI" className="w-full h-full object-contain" />
            <span className="absolute bottom-0 right-0 flex h-2 w-2">
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-slate-900 dark:text-white tracking-tight">
                Kiki AI
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-900/50 rounded-full flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Connected to FINPIXE
              </span>
            </div>
          </div>
        </div>

        {/* Right Action Controls: Search, New Chat, History, Settings, Expand, Close */}
        <div className="flex items-center gap-1">
          <button
            onClick={onSearchClick}
            title="Search conversation"
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <Search className="w-4 h-4" />
          </button>
          <button
            onClick={onNewChat}
            title="New Chat / Thread"
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={onToggleHistory}
            title="Conversation History"
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <Clock className="w-4 h-4" />
          </button>
          <button
            onClick={onToggleExpand}
            title={isExpanded ? "Collapse" : "Expand Command Center"}
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors hidden md:block cursor-pointer"
          >
            {isExpanded ? <Minimize className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={onClose}
            title="Close Command Center (Esc)"
            className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Sub Header ERP Context Bar Row */}
      <div className="px-4 py-1 bg-slate-50 dark:bg-slate-800/40 border-t border-[#E5E7EB] dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-500 font-medium">
        <div className="flex items-center gap-2 truncate">
          <span className="flex items-center gap-1 font-semibold text-slate-700 dark:text-slate-300">
            <Building2 className="w-3 h-3 text-[#FF8A00]" />
            <span>ABC Pvt Ltd</span>
          </span>
          <span>•</span>
          <span className="truncate">Chennai Branch</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">FY 2026-27</span>
        </div>
        <div className="flex items-center gap-1 font-mono text-[10px] text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-1.5 py-0.5 rounded shrink-0">
          <Zap className="w-3 h-3 text-[#FF8A00]" />
          <span>Local AI / Qwen2.5</span>
        </div>
      </div>
    </div>
  );
};
