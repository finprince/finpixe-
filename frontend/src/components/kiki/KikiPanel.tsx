import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AgentMessage } from '../../types';
import { KikiHeader } from './KikiHeader';
import { KikiHistorySidebar } from './KikiHistorySidebar';
import { KikiConversation } from './KikiConversation';
import { KikiSuggestionChip } from './KikiSuggestionChip';
import { KikiCommandInput } from './KikiCommandInput';
import { KikiContextFooter } from './KikiContextFooter';

interface KikiPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AgentMessage[];
  onSendMessage: (message: string, useGrounding: boolean) => void;
  isLoading: boolean;
  queueStatus?: {
    queuePosition?: number;
    estimatedWaitSeconds?: number;
    code?: string;
    retryAfter?: number;
  };
  onNavigate?: (route: string) => void;
}

const COMMAND_CHIPS = [
  "Today's Sales",
  "Pending Purchases",
  "GST Summary",
  "Cash Flow",
  "Top Vendors",
  "Recent Payments",
  "Inventory Status"
];

export const KikiPanel: React.FC<KikiPanelProps> = ({
  isOpen,
  onClose,
  messages,
  onSendMessage,
  isLoading,
  queueStatus,
  onNavigate
}) => {
  const [input, setInput] = useState('');
  const [useGrounding, setUseGrounding] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleSend = (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (query && !isLoading) {
      onSendMessage(query, useGrounding);
      setInput('');
    }
  };

  const handleNavigate = (route: string) => {
    if (onNavigate) {
      onNavigate(route);
    } else {
      window.history.pushState({}, '', route);
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  };

  if (!isOpen) return null;

  const showChips = messages.length <= 1;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 pointer-events-none flex items-end justify-end p-3 sm:p-5 overflow-hidden font-sans">
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.98 }}
          transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
          className={`pointer-events-auto relative flex flex-col bg-[#F8FAFC]/95 dark:bg-slate-900/95 backdrop-blur-xl border border-[#E5E7EB] dark:border-slate-800 shadow-[0_20px_50px_-10px_rgba(0,0,0,0.1)] transition-all duration-300 overflow-hidden ${isExpanded
              ? 'w-[92vw] md:w-[760px] h-[92vh] rounded-2xl'
              : 'w-full md:w-[480px] h-[86vh] max-h-[840px] rounded-2xl'
            }`}
        >
          {/* History Drawer Overlay */}
          <KikiHistorySidebar
            isOpen={showHistory}
            onClose={() => setShowHistory(false)}
            onSelectSession={() => { }}
            onNewChat={() => { }}
          />

          {/* Compact Modern Header */}
          <KikiHeader
            onToggleHistory={() => setShowHistory(!showHistory)}
            isExpanded={isExpanded}
            onToggleExpand={() => setIsExpanded(!isExpanded)}
            onClose={onClose}
          />

          {/* AI Report Workspace Feed */}
          <KikiConversation
            messages={messages}
            isLoading={isLoading}
            onSendPrompt={handleSend}
            onNavigate={handleNavigate}
          />

          {/* Neutral Command Suggestion Pills */}
          <KikiSuggestionChip
            chips={COMMAND_CHIPS}
            onSelectChip={(chip) => setInput(chip)}
            visible={showChips}
          />

          {/* Floating Command Bar Input */}
          <KikiCommandInput
            input={input}
            onChange={setInput}
            onSend={handleSend}
            isLoading={isLoading}
            useGrounding={useGrounding}
            onToggleGrounding={() => setUseGrounding(!useGrounding)}
          />

          {/* Context Footer Bar */}
          <KikiContextFooter />
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
