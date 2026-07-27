import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Layers, FileText, PieChart, FileSpreadsheet } from 'lucide-react';

interface KikiActionCardProps {
  title: string;
  description: string;
  route: string;
  icon?: string;
  onOpen: (route: string) => void;
}

export const KikiActionCard: React.FC<KikiActionCardProps> = ({
  title,
  description,
  route,
  onOpen
}) => {
  return (
    <motion.div
      whileHover={{ scale: 1.01, transition: { duration: 0.15 } }}
      className="p-4 rounded-xl bg-gradient-to-r from-slate-50 to-white dark:from-slate-900/90 dark:to-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs hover:shadow-md hover:border-[#5B5CEB]/50 transition-all duration-200 my-2 group"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-[#5B5CEB] to-[#7C3AED] text-white flex items-center justify-center shrink-0 shadow-xs">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-900 dark:text-white tracking-tight">
              {title}
            </h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {description}
            </p>
          </div>
        </div>

        <button
          onClick={() => onOpen(route)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#5B5CEB] dark:text-[#6D7CFF] bg-[#5B5CEB]/10 hover:bg-[#5B5CEB] hover:text-white rounded-lg transition-all duration-150 cursor-pointer shrink-0"
        >
          <span>Open</span>
          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
};
