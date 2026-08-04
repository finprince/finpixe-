import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

interface NavigationOption {
  title: string;
  route: string;
  description?: string;
  category?: string;
}

interface KikiNavigationCardProps {
  options: NavigationOption[];
  onSelectOption: (route: string) => void;
}

export const KikiNavigationCard: React.FC<KikiNavigationCardProps> = ({
  options,
  onSelectOption
}) => {
  if (!options || options.length === 0) return null;

  return (
    <div className="space-y-2 my-3">
      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
        <ArrowRight className="w-4 h-4 text-[#FF8A00]" />
        <span>Choose where you want to go</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {options.map((opt, idx) => (
          <motion.button
            key={idx}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            onClick={() => onSelectOption(opt.route)}
            className="flex flex-col justify-between p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 hover:border-[#FF8A00] dark:hover:border-[#FF8A00] hover:shadow-md text-left transition-all duration-200 group cursor-pointer"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-[#FF8A00] transition-colors">
                  {opt.title}
                </span>
                {opt.category && (
                  <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                    {opt.category}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                {opt.description || `Launch and manage ${opt.title} workspace.`}
              </p>
            </div>

            <div className="flex items-center justify-end gap-1 text-xs font-semibold text-[#FF8A00] mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
              <span>Open</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
};
