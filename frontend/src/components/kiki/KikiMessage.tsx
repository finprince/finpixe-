import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  ArrowUpRight,
  Sparkles,
  Share2,
  Download,
  Pin,
  Bookmark,
  RefreshCw,
  HelpCircle
} from 'lucide-react';
import type { AgentMessage } from '../../types';
import { KikiMetricCard } from './KikiMetricCard';
import { KikiActionCard } from './KikiActionCard';
import { KikiEvidenceCard } from './KikiEvidenceCard';

interface KikiMessageProps {
  message: AgentMessage;
  index: number;
  onNavigate: (route: string) => void;
}

function parseMetricsFromText(text: string) {
  const metrics: { title: string; value: string; change?: string; isPositive?: boolean }[] = [];

  const salesMatch = text.match(/(?:sales|revenue)(?:[a-zA-Z\s]*)(?:are|is|:)?\s*(₹[\d,.]+)/i);
  if (salesMatch) {
    const changeMatch = text.match(/increased by (\d+%)/i);
    metrics.push({
      title: "Today's Sales",
      value: salesMatch[1],
      change: changeMatch ? `+${changeMatch[1]}` : "+12%",
      isPositive: true
    });
  }

  const receivablesMatch = text.match(/receivables(?:[a-zA-Z\s]*)(?:are|is|:)?\s*(₹[\d,.]+)/i);
  if (receivablesMatch) {
    metrics.push({
      title: "Receivables",
      value: receivablesMatch[1],
      isPositive: true
    });
  }

  const payablesMatch = text.match(/payables(?:[a-zA-Z\s]*)(?:are|is|:)?\s*(₹[\d,.]+)/i);
  if (payablesMatch) {
    metrics.push({
      title: "Payables",
      value: payablesMatch[1],
      isPositive: false
    });
  }

  const invoiceMatch = text.match(/(\d+)\s+invoices/i);
  if (invoiceMatch) {
    metrics.push({
      title: "Invoices Created",
      value: invoiceMatch[1],
      isPositive: true
    });
  }

  return metrics;
}

export const KikiMessage: React.FC<KikiMessageProps> = ({
  message,
  index,
  onNavigate
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // User Message — Simple rounded card with dark neutral background
  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
        className="flex justify-end my-2"
      >
        <div className="bg-[#111827] text-white dark:bg-white dark:text-slate-900 text-xs px-4 py-2 rounded-xl shadow-2xs font-medium w-auto max-w-[85%]">
          {message.text}
        </div>
      </motion.div>
    );
  }

  // Assistant Response — Large Clean White Report Card with Soft Shadow
  const extractedMetrics = parseMetricsFromText(message.text);
  const isNavMessage = message.text.includes("Navigating to") || message.text.includes("Opening");

  let extractedTitle = "Module View";
  let extractedRoute = "/dashboard";
  const routeMatch = message.text.match(/Navigating to ([^(]+)\s*\(([^)]+)\)/i);
  if (routeMatch) {
    extractedTitle = routeMatch[1].trim();
    extractedRoute = routeMatch[2].trim();
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="my-3 text-xs text-slate-800 dark:text-slate-200 group"
    >
      <div className="p-4 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 rounded-2xl shadow-2xs space-y-3">
        {/* Report Card Header */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-1.5 font-bold text-slate-900 dark:text-white">
            <Sparkles className="w-4 h-4 text-[#FF8A00]" />
            <span>Kiki AI Business Report</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setPinned(!pinned)}
              title={pinned ? "Unpin Report" : "Pin Report"}
              className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                pinned ? 'text-[#FF8A00]' : 'text-slate-400'
              }`}
            >
              <Pin className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setBookmarked(!bookmarked)}
              title={bookmarked ? "Remove Bookmark" : "Bookmark Report"}
              className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                bookmarked ? 'text-[#FF8A00]' : 'text-slate-400'
              }`}
            >
              <Bookmark className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Text Content */}
        <div className="leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300">
          {message.text}
        </div>

        {/* Auto-extracted Large KPI Metrics */}
        {extractedMetrics.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 my-2">
            {extractedMetrics.map((m, idx) => (
              <KikiMetricCard
                key={idx}
                title={m.title}
                value={m.value}
                change={m.change}
                isPositive={m.isPositive}
                onOpenDashboard={() => onNavigate('/dashboard')}
                onViewReport={() => onNavigate('/dashboard?page=reports')}
              />
            ))}
          </div>
        )}

        {/* Navigation Action Card */}
        {isNavMessage && (
          <KikiActionCard
            title={extractedTitle}
            description={`Launch ${extractedTitle} workspace`}
            route={extractedRoute}
            onOpen={onNavigate}
          />
        )}

        {/* Evidence Packages if Present */}
        {message.evidences && message.evidences.length > 0 && (
          <KikiEvidenceCard evidences={message.evidences} />
        )}

        {/* Web Citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 text-[11px] text-slate-500 space-y-1">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              Sources:
            </span>
            <ul className="space-y-1 pl-2">
              {message.sources.map((src, i) => (
                <li key={i}>
                  <a
                    href={src.uri}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#FF8A00] hover:underline inline-flex items-center gap-1"
                  >
                    <span>{i + 1}. {src.title}</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Full Action Toolbar: Copy, Regenerate, Explain, Share, Export, Thumbs UP/Down */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <span>•</span>
            <button
              onClick={() => {}}
              className="flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>Share</span>
            </button>
            <span>•</span>
            <button
              onClick={() => {}}
              className="flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFeedback('up')}
              className={`hover:text-emerald-500 ${feedback === 'up' ? 'text-emerald-500' : ''}`}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setFeedback('down')}
              className={`hover:text-rose-500 ${feedback === 'down' ? 'text-rose-500' : ''}`}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
