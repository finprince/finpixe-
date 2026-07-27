import React, { useRef, useEffect } from 'react';
import { Sparkles, PieChart, Layers, FileText, TrendingUp, ShieldCheck, FileSpreadsheet, ChevronRight, LayoutDashboard, Search } from 'lucide-react';
import type { AgentMessage } from '../../types';
import { KikiMessage } from './KikiMessage';
import { KikiTypingIndicator } from './KikiTypingIndicator';
import kikiLogo from '../../assets/kiki-agent-orange.png';

interface KikiConversationProps {
  messages: AgentMessage[];
  isLoading: boolean;
  onSendPrompt: (promptText: string) => void;
  onNavigate: (route: string) => void;
}

const EMPTY_STATE_ACTIONS = [
  { label: "Today's Sales", prompt: "Show today's sales summary" },
  { label: "GST Filing Summary", prompt: "Give me a GST filing summary" },
  { label: "Pending Purchases", prompt: "Show pending purchase requisitions" },
  { label: "Create Voucher", prompt: "How do I create a voucher entry?" },
  { label: "Open Dashboard", prompt: "Go to Dashboard" },
  { label: "Analyze Cash Flow", prompt: "Analyze current cash flow" },
  { label: "Search Vendor", prompt: "Go to Vendor Portal" }
];

const CAPABILITY_CARDS = [
  {
    icon: PieChart,
    title: "Generate Reports",
    description: "Financial statements, Balance Sheet, P&L analytics",
    prompt: "Generate financial statements and P&L report for this period"
  },
  {
    icon: Layers,
    title: "Open Pages",
    description: "Quick navigation to Vendor Portal, Inventory, Vouchers",
    prompt: "Go to Vendor Portal"
  },
  {
    icon: FileText,
    title: "Search Invoices",
    description: "Scan OCR bills, purchase receipts, and vouchers",
    prompt: "Show recent purchase invoices"
  },
  {
    icon: TrendingUp,
    title: "Analyze Ledgers",
    description: "Chart of accounts, customer balances, party ledgers",
    prompt: "Analyze top customer balances and accounts"
  },
  {
    icon: ShieldCheck,
    title: "Explain GST",
    description: "GSTR-1, GSTR-3B filings, tax reconciliation",
    prompt: "Give me a GST compliance and filing summary"
  },
  {
    icon: FileSpreadsheet,
    title: "Create Vouchers",
    description: "Sales, Purchase, Payment & Receipt entries",
    prompt: "How do I create a sales voucher entry?"
  }
];

export const KikiConversation: React.FC<KikiConversationProps> = ({
  messages,
  isLoading,
  onSendPrompt,
  onNavigate
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800">
      {messages.length <= 1 ? (
        /* Empty State Screen */
        <div className="py-2 space-y-4">
          <div className="p-5 rounded-2xl bg-gradient-to-br from-orange-50/50 via-slate-50 to-white dark:from-slate-800/40 dark:via-slate-900 dark:to-slate-900 border border-[#E5E7EB] dark:border-slate-800 shadow-2xs">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-xl bg-orange-50 border border-orange-200/60 p-0.5 shrink-0 shadow-2xs">
                <img src={kikiLogo} alt="Kiki AI" className="w-full h-full object-contain" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-[#FF8A00]">
                FINPIXE AI Command Center
              </span>
            </div>
            <h4 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
              👋 Welcome back
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-medium">
              What would you like to do today?
            </p>

            {/* Quick Actions Tiles */}
            <div className="mt-3 flex flex-wrap gap-1.5">
              {EMPTY_STATE_ACTIONS.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendPrompt(action.prompt)}
                  className="px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 rounded-xl hover:border-[#FF8A00] hover:text-[#FF8A00] transition-all shadow-2xs cursor-pointer"
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-1">
              Command Center Capabilities
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {CAPABILITY_CARDS.map((card, idx) => {
                const CardIcon = card.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => onSendPrompt(card.prompt)}
                    className="flex flex-col text-left p-3.5 rounded-xl bg-white dark:bg-slate-800/60 border border-[#E5E7EB] dark:border-slate-800 hover:border-[#FF8A00] dark:hover:border-[#FF8A00] hover:shadow-xs transition-all duration-200 group cursor-pointer"
                  >
                    <div className="flex items-center justify-between w-full mb-1.5">
                      <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-700/60 text-slate-700 dark:text-slate-300 group-hover:bg-[#FF8A00] group-hover:text-white transition-colors">
                        <CardIcon className="w-4 h-4" />
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-[#FF8A00] transition-colors" />
                    </div>
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      {card.title}
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                      {card.description}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* AI Workspace Report Feed */
        messages.map((msg, idx) => (
          <KikiMessage
            key={idx}
            message={msg}
            index={idx}
            onNavigate={onNavigate}
          />
        ))
      )}

      {/* Streaming Progress Indicator */}
      {isLoading && <KikiTypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
};
