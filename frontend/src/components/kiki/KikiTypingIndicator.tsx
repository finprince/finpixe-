import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, CheckCircle2 } from 'lucide-react';

const THINKING_STEPS = [
  "Thinking...",
  "Understanding your request...",
  "Analyzing ERP context...",
  "Searching application...",
  "Preparing answer..."
];

export const KikiTypingIndicator: React.FC = () => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex(prev => (prev + 1) % THINKING_STEPS.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      className="my-3 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 shadow-2xs space-y-2.5"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
          <Sparkles className="w-4 h-4 text-[#FF8A00]" />
          <span>{THINKING_STEPS[stepIndex]}</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">Processing...</span>
      </div>

      {/* Smooth Progress Line Indicator */}
      <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-[#FF8A00] to-amber-500 rounded-full"
          initial={{ width: '15%' }}
          animate={{ width: `${((stepIndex + 1) / THINKING_STEPS.length) * 100}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 pt-1">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
        <span>Connected to FINPIXE Live Database</span>
      </div>
    </motion.div>
  );
};
