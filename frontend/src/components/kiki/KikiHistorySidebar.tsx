import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Layers, FileText, Trash2, X, Plus } from 'lucide-react';

interface HistorySession {
  id: string;
  title: string;
  timestamp: string;
  group: 'Today' | 'Yesterday' | 'Last Week' | 'Pinned';
}

interface KikiHistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
}

const MOCK_SESSIONS: HistorySession[] = [
  { id: '1', title: 'Sales decrease analysis & top customers', timestamp: '10:42 AM', group: 'Today' },
  { id: '2', title: 'Navigation to Vendor Portal & Purchase Orders', timestamp: '09:15 AM', group: 'Today' },
  { id: '3', title: 'Trial Balance & Ledger Reconciliation', timestamp: 'Yesterday', group: 'Yesterday' },
  { id: '4', title: 'GSTR-1 tax filing summary', timestamp: 'Jul 24', group: 'Last Week' },
  { id: '5', title: 'Monthly Profit & Loss Statement audit', timestamp: 'Jul 21', group: 'Pinned' }
];

export const KikiHistorySidebar: React.FC<KikiHistorySidebarProps> = ({
  isOpen,
  onClose,
  onSelectSession,
  onNewChat
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [sessions, setSessions] = useState<HistorySession[]>(MOCK_SESSIONS);

  if (!isOpen) return null;

  const filtered = sessions.filter(s =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groups = ['Pinned', 'Today', 'Yesterday', 'Last Week'] as const;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="absolute inset-y-0 left-0 z-30 w-72 bg-slate-900 text-slate-100 p-4 shadow-2xl rounded-l-2xl flex flex-col border-r border-slate-800"
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          History & Threads
        </h4>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-white rounded-md transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="my-3 flex items-center gap-2">
        <button
          onClick={onNewChat}
          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-[#5B5CEB] hover:bg-[#4b4cd4] text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Workspace Thread</span>
        </button>
      </div>

      <div className="relative mb-3">
        <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search past threads..."
          className="w-full pl-8 pr-3 py-1.5 bg-slate-800/80 border border-slate-700/60 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-[#5B5CEB]"
        />
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-thin scrollbar-thumb-slate-800">
        {groups.map(groupName => {
          const groupItems = filtered.filter(s => s.group === groupName);
          if (groupItems.length === 0) return null;

          return (
            <div key={groupName} className="space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
                {groupName}
              </span>
              {groupItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectSession(item.id);
                    onClose();
                  }}
                  className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/80 text-left text-xs transition-colors group cursor-pointer"
                >
                  <div className="flex items-center gap-2 truncate">
                    {groupName === 'Pinned' ? (
                      <Layers className="w-3 h-3 text-[#FF8A00] shrink-0" />
                    ) : (
                      <FileText className="w-3 h-3 text-slate-500 shrink-0" />
                    )}
                    <span className="truncate text-slate-300 group-hover:text-white">
                      {item.title}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          );
        })}
      </div>
    </motion.div>
  );
};
