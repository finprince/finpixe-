import React, { useState } from 'react';
import { X, Activity, Sparkles, Clock, FileText, ChevronRight } from 'lucide-react';
import type { InspectorState } from '../../types';

interface InspectorDrawerProps {
  state: InspectorState;
  onClose: () => void;
}

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({ state, onClose }) => {
  const [activeTab, setActiveTab] = useState<'properties' | 'activity' | 'ai'>('properties');

  if (!state.isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-[320px] bg-white border-l border-slate-200 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 text-[#4F46E5] flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div className="truncate">
            <h3 className="text-sm font-bold text-slate-900 truncate">{state.title || 'Record Inspector'}</h3>
            <p className="text-[10px] font-medium text-slate-400 truncate">{state.subtitle || state.entityType || 'Entity Properties'}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-100 bg-white">
        <button
          onClick={() => setActiveTab('properties')}
          className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'properties' ? 'border-[#4F46E5] text-[#4F46E5]' : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Properties
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'activity' ? 'border-[#4F46E5] text-[#4F46E5]' : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Activity
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'ai' ? 'border-[#4F46E5] text-[#4F46E5]' : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          AI Insights
        </button>
      </div>

      {/* Drawer Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'properties' && (
          <div className="space-y-3">
            {!state.data || Object.keys(state.data).length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 font-medium">
                No active record selected. Click any row or item to inspect properties.
              </div>
            ) : (
              Object.entries(state.data).map(([key, val]) => (
                <div key={key} className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex flex-col gap-0.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{key.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-semibold text-slate-800 break-words">{String(val ?? '—')}</span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="space-y-3">
            {(!state.activityLogs || state.activityLogs.length === 0) ? (
              <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl text-xs text-slate-500">
                <Clock className="w-4 h-4 text-slate-400 shrink-0" />
                <span>No historical edit logs recorded for this entity.</span>
              </div>
            ) : (
              state.activityLogs.map(log => (
                <div key={log.id} className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
                    {log.user.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{log.action}</p>
                    <span className="text-[10px] font-medium text-slate-400">{log.timestamp} • {log.user}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-3">
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl flex items-start gap-2.5">
              <Sparkles className="w-4 h-4 text-[#4F46E5] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-[#4F46E5]">AI Assistant Context</h4>
                <p className="text-[11px] font-medium text-slate-600 mt-0.5">
                  Automated anomaly checks and predictive reorder insights are active for this entity.
                </p>
              </div>
            </div>

            {state.aiRecommendations?.map(rec => (
              <div key={rec.id} className="p-3 bg-white border border-slate-200 rounded-xl shadow-xs flex items-center justify-between">
                <span className="text-xs font-medium text-slate-700">{rec.text}</span>
                {rec.confidence && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {rec.confidence}%
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-[10px] text-slate-400 font-bold uppercase tracking-wider">
        <span>Finpixe AI Operating System</span>
        <span>v2.0</span>
      </div>
    </div>
  );
};
