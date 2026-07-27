import React from 'react';
import { motion } from 'framer-motion';

interface KikiSuggestionChipProps {
  chips: string[];
  onSelectChip: (chipText: string) => void;
  visible: boolean;
}

export const KikiSuggestionChip: React.FC<KikiSuggestionChipProps> = ({
  chips,
  onSelectChip,
  visible
}) => {
  if (!visible || chips.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      className="px-4 py-2 bg-[#F8FAFC]/80 dark:bg-slate-900/80 border-t border-[#E5E7EB] dark:border-slate-800/80 overflow-x-auto whitespace-nowrap scrollbar-none flex items-center gap-1.5 shrink-0 select-none"
    >
      {chips.map((chip, idx) => (
        <button
          key={idx}
          onClick={() => onSelectChip(chip)}
          className="inline-flex items-center px-3 py-1 text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700/80 rounded-full hover:border-[#FF8A00] hover:text-[#FF8A00] dark:hover:border-[#FF8A00] dark:hover:text-[#FF8A00] transition-colors shrink-0 shadow-2xs cursor-pointer"
        >
          <span>{chip}</span>
        </button>
      ))}
    </motion.div>
  );
};
