import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, ArrowUpRight, Download, Copy, Check } from 'lucide-react';

interface KikiMetricCardProps {
  title: string;
  value: string;
  change?: string;
  comparedTo?: string;
  isPositive?: boolean;
  onOpenDashboard?: () => void;
  onViewReport?: () => void;
}

export const KikiMetricCard: React.FC<KikiMetricCardProps> = ({
  title,
  value,
  change,
  comparedTo = "compared to yesterday",
  isPositive = true,
  onOpenDashboard,
  onViewReport
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(`${title}: ${value} (${change || ''})`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 shadow-2xs hover:shadow-md transition-all duration-200 group flex flex-col justify-between my-2"
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
            {title}
          </span>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              title="Copy Metric"
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>
        </div>

        <div className="flex items-baseline gap-2.5 my-1">
          <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            {value}
          </span>

          {change && (
            <span
              className={`inline-flex items-center gap-0.5 text-xs font-bold px-1.5 py-0.5 rounded-md ${
                isPositive
                  ? 'text-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 dark:text-emerald-400'
                  : 'text-rose-700 bg-rose-50 dark:bg-rose-950/40 dark:text-rose-400'
              }`}
            >
              {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
              {change}
            </span>
          )}
        </div>

        {comparedTo && (
          <p className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
            {comparedTo}
          </p>
        )}

        {/* Mini Sparkline Bar Chart Indicator */}
        <div className="flex items-end gap-1 h-4 mt-3 pt-1 border-t border-slate-100 dark:border-slate-800">
          <div className="flex-1 bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${isPositive ? 'bg-emerald-500' : 'bg-rose-500'}`}
              style={{ width: '72%' }}
            />
          </div>
        </div>
      </div>

      {/* KPI Action Buttons */}
      <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        <button
          onClick={onOpenDashboard}
          className="flex-1 inline-flex items-center justify-center gap-1 py-1 px-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-[11px] font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <span>Open Dashboard</span>
          <ArrowUpRight className="w-3 h-3 text-slate-400" />
        </button>
        <button
          onClick={onViewReport}
          className="flex-1 inline-flex items-center justify-center gap-1 py-1 px-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-[11px] font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <span>View Report</span>
          <ArrowUpRight className="w-3 h-3 text-slate-400" />
        </button>
      </div>
    </motion.div>
  );
};
