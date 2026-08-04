import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Check,
  ArrowUpRight,
  Sparkles,
  Share2,
  Download,
  ChevronDown,
  ChevronUp,
  Info,
  FileText,
  ArrowRight,
  Layers
} from 'lucide-react';
import type { AgentMessage, RecommendationItem, QuickActionItem } from '../../types';
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
  const [showDeveloperMode, setShowDeveloperMode] = useState(false);
  const [activeDevTab, setActiveDevTab] = useState<'planner' | 'knowledge' | 'reflection' | 'telemetry'>('planner');

  const handleCopy = () => {
    navigator.clipboard.writeText(message.text || message.summary || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // User Message — Simple rounded card
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

  // Assistant Response — Senior ERP Consultant Business Report
  const extractedMetrics = parseMetricsFromText(message.text || '');
  const title = message.title || "Kiki AI Business Report";
  const resultVal = message.result;
  const summaryText = message.summary || message.text;
  const insights = message.insights || [];
  const recommendations: RecommendationItem[] = message.recommendations || [];
  const quickActions: QuickActionItem[] = message.quickActions || [];
  const devDetails = message.developerDetails;
  const confidence = message.confidence || 'HIGH';
  const persona = message.persona || 'Accountant';

  const hasTechnicalData = Boolean(
    devDetails || (message.evidences && message.evidences.length > 0)
  );

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
          <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
            <Sparkles className="w-4 h-4 text-[#FF8A00]" />
            <span>{title}</span>
            {persona && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-50 text-[#FF8A00] dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40">
                {persona}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {/* Confidence Badge */}
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                confidence === 'HIGH'
                  ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40'
                  : confidence === 'MEDIUM'
                  ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
              }`}
            >
              {confidence} Confidence
            </span>

            <button
              onClick={() => setPinned(!pinned)}
              title={pinned ? "Unpin Report" : "Pin Report"}
              className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                pinned ? 'text-[#FF8A00]' : 'text-slate-400'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setBookmarked(!bookmarked)}
              title={bookmarked ? "Remove Bookmark" : "Bookmark Report"}
              className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                bookmarked ? 'text-[#FF8A00]' : 'text-slate-400'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Primary Metric Result Banner (If Present) */}
        {resultVal && (
          <div className="p-3 rounded-xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-[#FF8A00]/20 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Key Result Metric
              </span>
              <div className="text-xl font-extrabold text-[#FF8A00] mt-0.5">
                {resultVal}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-[#FF8A00]/10 text-[#FF8A00]">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
        )}

        {/* Business Summary Content */}
        <div className="leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300">
          {summaryText}
        </div>

        {/* Key Business Insights Section */}
        {insights.length > 0 && (
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-800 dark:text-slate-200">
              <Info className="w-3.5 h-3.5 text-[#FF8A00]" />
              <span>Key Business Insights</span>
            </div>
            <ul className="space-y-1 pl-4 list-disc text-slate-600 dark:text-slate-300 text-[11px]">
              {insights.map((insight, idx) => (
                <li key={idx}>{insight}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Quick Actions Buttons for Business Users */}
        {quickActions.length > 0 && (
          <div className="p-2.5 rounded-xl bg-[#FF8A00]/5 border border-[#FF8A00]/20 flex flex-wrap gap-2 items-center">
            <span className="text-[10px] font-bold text-[#FF8A00] uppercase tracking-wide">
              Quick Actions:
            </span>
            {quickActions.map((qa, idx) => (
              <button
                key={idx}
                onClick={() => {
                  if (qa.route) onNavigate(qa.route);
                }}
                className="px-2.5 py-1 bg-[#FF8A00] hover:bg-[#e07a00] text-white font-semibold text-[10px] rounded-md transition-colors shadow-2xs cursor-pointer flex items-center gap-1"
              >
                <span>{qa.title}</span>
                <ArrowUpRight className="w-3 h-3" />
              </button>
            ))}
          </div>
        )}

        {/* Recommendation Engine Next Actions */}
        {recommendations.length > 0 && (
          <div className="pt-2 space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              <ArrowRight className="w-3.5 h-3.5 text-[#FF8A00]" />
              <span>Recommended Next Actions</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {recommendations.map((rec, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (rec.route) onNavigate(rec.route);
                  }}
                  className="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-[#FF8A00] dark:hover:border-[#FF8A00] text-slate-700 dark:text-slate-200 hover:text-[#FF8A00] transition-all shadow-2xs text-[11px] font-medium cursor-pointer"
                >
                  <span>{rec.title}</span>
                  <ArrowUpRight className="w-3 h-3 text-slate-400 group-hover:text-[#FF8A00] transition-colors" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Developer Mode / Explain My Answer Toggle */}
        {hasTechnicalData && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setShowDeveloperMode(!showDeveloperMode)}
              className="flex items-center justify-between w-full px-3 py-2 rounded-xl bg-slate-100/70 dark:bg-slate-800/60 hover:bg-slate-200/70 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-[11px] font-semibold transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-[#FF8A00]" />
                <span>Explain My Answer / Developer Mode</span>
              </div>
              <div className="flex items-center gap-1 text-slate-400 text-[10px]">
                <span>{showDeveloperMode ? 'Hide Telemetry' : 'Show Telemetry & Planner'}</span>
                {showDeveloperMode ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </div>
            </button>

            <AnimatePresence>
              {showDeveloperMode && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="mt-2 p-3 rounded-xl bg-slate-900 text-slate-200 font-mono text-[10px] space-y-3 overflow-hidden shadow-inner border border-slate-800"
                >
                  {/* Dev Tab Navigation */}
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto text-[10px] font-sans">
                    <button
                      onClick={() => setActiveDevTab('planner')}
                      className={`px-2 py-1 rounded transition-colors ${
                        activeDevTab === 'planner'
                          ? 'bg-[#FF8A00] text-white font-bold'
                          : 'text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      Planner
                    </button>
                    <button
                      onClick={() => setActiveDevTab('knowledge')}
                      className={`px-2 py-1 rounded transition-colors ${
                        activeDevTab === 'knowledge'
                          ? 'bg-[#FF8A00] text-white font-bold'
                          : 'text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      Vector Knowledge ({devDetails?.retrieved_knowledge?.length || 0})
                    </button>
                    <button
                      onClick={() => setActiveDevTab('reflection')}
                      className={`px-2 py-1 rounded transition-colors ${
                        activeDevTab === 'reflection'
                          ? 'bg-[#FF8A00] text-white font-bold'
                          : 'text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      Reflection
                    </button>
                    <button
                      onClick={() => setActiveDevTab('telemetry')}
                      className={`px-2 py-1 rounded transition-colors ${
                        activeDevTab === 'telemetry'
                          ? 'bg-[#FF8A00] text-white font-bold'
                          : 'text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      SQL & Skills ({devDetails?.sql_queries?.length || 0})
                    </button>
                  </div>

                  {/* Tab 1: Planner Output */}
                  {activeDevTab === 'planner' && (
                    <div className="space-y-1.5">
                      <div className="text-amber-400 font-sans font-bold text-xs">
                        Cognitive Planner Execution Plan:
                      </div>
                      <pre className="p-2 rounded bg-slate-950 text-slate-300 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(devDetails?.planner_output || message.executionPlan || {}, null, 2)}
                      </pre>
                      <div className="text-slate-400 font-sans text-[10px]">
                        Skills Selected: {devDetails?.skills_executed?.join(', ') || 'KPISkill, InvestigationSkill'}
                      </div>
                    </div>
                  )}

                  {/* Tab 2: Vector Knowledge Retrieval */}
                  {activeDevTab === 'knowledge' && (
                    <div className="space-y-1.5">
                      <div className="text-amber-400 font-sans font-bold text-xs">
                        Retrieved Semantic Vector Knowledge:
                      </div>
                      {devDetails?.retrieved_knowledge && devDetails.retrieved_knowledge.length > 0 ? (
                        devDetails.retrieved_knowledge.map((k, i) => (
                          <div key={i} className="p-2 rounded bg-slate-950 border border-slate-800 space-y-1">
                            <div className="flex items-center justify-between text-emerald-400 font-bold">
                              <span>{k.title}</span>
                              <span className="text-[9px] text-slate-400">Score: {k.relevance_score}</span>
                            </div>
                            <p className="text-slate-300 text-[10px]">{k.content}</p>
                          </div>
                        ))
                      ) : (
                        <div className="text-slate-400 italic">No vector knowledge retrieved for this query.</div>
                      )}
                    </div>
                  )}

                  {/* Tab 3: Reflection Summary */}
                  {activeDevTab === 'reflection' && (
                    <div className="space-y-1.5">
                      <div className="text-amber-400 font-sans font-bold text-xs">
                        Reflection Engine Quality Audit:
                      </div>
                      <pre className="p-2 rounded bg-slate-950 text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(devDetails?.reflection_summary || message.reflection || {}, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Tab 4: SQL & Skill Execution Telemetry */}
                  {activeDevTab === 'telemetry' && (
                    <div className="space-y-1.5">
                      <div className="text-amber-400 font-sans font-bold text-xs">
                        Executed SQL Statements & Telemetry:
                      </div>
                      {devDetails?.sql_queries && devDetails.sql_queries.length > 0 ? (
                        devDetails.sql_queries.map((q, i) => (
                          <pre key={i} className="p-2 rounded bg-slate-950 text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                            {q}
                          </pre>
                        ))
                      ) : (
                        <div className="text-slate-400 italic">No direct SQL queries executed (Resolved via fast-path skill).</div>
                      )}

                      {message.evidences && message.evidences.length > 0 && (
                        <KikiEvidenceCard evidences={message.evidences} />
                      )}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
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

        {/* Action Toolbar */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <FileText className="w-3.5 h-3.5" />}
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
              <span>👍</span>
            </button>
            <button
              onClick={() => setFeedback('down')}
              className={`hover:text-rose-500 ${feedback === 'down' ? 'text-rose-500' : ''}`}
            >
              <span>👎</span>
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
