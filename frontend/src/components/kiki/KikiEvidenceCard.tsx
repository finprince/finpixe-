import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, FileText, Database, Layers } from 'lucide-react';

interface EvidenceItem {
  title: string;
  query?: string;
  rowCount?: number;
  data?: Record<string, any>[];
}

interface KikiEvidenceCardProps {
  evidences: EvidenceItem[];
}

export const KikiEvidenceCard: React.FC<KikiEvidenceCardProps> = ({ evidences }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!evidences || evidences.length === 0) return null;

  return (
    <div className="my-2.5 rounded-xl border border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between bg-slate-50/80 dark:bg-slate-800/40 text-left hover:bg-slate-100/60 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
          <Database className="w-3.5 h-3.5 text-[#FF8A00]" />
          <span>ERP Evidence Packages ({evidences.length})</span>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-slate-400">
          <span>{isOpen ? 'Collapse' : 'Expand Details'}</span>
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="p-3 space-y-2 text-xs border-t border-[#E5E7EB] dark:border-slate-800"
          >
            {evidences.map((ev, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
                <div className="flex items-center justify-between font-medium text-slate-900 dark:text-white mb-1">
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3 h-3 text-slate-500" />
                    {ev.title}
                  </span>
                  {ev.rowCount !== undefined && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-slate-700 dark:text-slate-300">
                      {ev.rowCount} rows
                    </span>
                  )}
                </div>
                {ev.query && (
                  <pre className="p-1.5 rounded bg-slate-900 text-slate-100 text-[10px] font-mono overflow-x-auto my-1">
                    {ev.query}
                  </pre>
                )}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
