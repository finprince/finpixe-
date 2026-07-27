import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Search, Command, X, ArrowRight } from 'lucide-react';
import type { CommandAction } from '../../types/types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  actions: CommandAction[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, actions }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredActions = useMemo(() => {
    if (!query.trim()) return actions;
    const q = query.toLowerCase();
    return actions.filter(
      a => a.title.toLowerCase().includes(q) || a.category.toLowerCase().includes(q)
    );
  }, [actions, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % (filteredActions.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredActions.length) % (filteredActions.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredActions[selectedIndex]) {
        filteredActions[selectedIndex].perform();
        onClose();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-100 bg-slate-50/50">
          <Search className="w-5 h-5 text-slate-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, page, or search query (e.g. Sales, Trial Balance)..."
            className="w-full bg-transparent text-sm font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none"
            role="combobox"
            aria-expanded="true"
            aria-haspopup="listbox"
          />
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50 transition-colors ml-2"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action Results List */}
        <div className="max-h-80 overflow-y-auto p-2 divide-y divide-slate-50">
          {filteredActions.length === 0 ? (
            <div className="p-8 text-center text-sm font-medium text-slate-400">
              No matching commands or pages found.
            </div>
          ) : (
            filteredActions.map((action, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={action.id}
                  onClick={() => {
                    action.perform();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer transition-colors ${
                    isSelected ? 'bg-[#EEF2FF] text-[#4F46E5]' : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isSelected ? 'bg-indigo-100 text-[#4F46E5]' : 'bg-slate-100 text-slate-500'}`}>
                      <Command className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold leading-tight">{action.title}</p>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{action.category}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {action.shortcut && (
                      <kbd className="px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-500 bg-slate-100 rounded border border-slate-200">
                        {action.shortcut}
                      </kbd>
                    )}
                    <ArrowRight className={`w-4 h-4 transition-transform ${isSelected ? 'translate-x-1 opacity-100' : 'opacity-0'}`} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer Shortcut Hints */}
        <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-xs text-slate-400 font-medium">
          <div className="flex gap-4">
            <span><kbd className="font-mono bg-white px-1.5 py-0.5 rounded border">↑</kbd> <kbd className="font-mono bg-white px-1.5 py-0.5 rounded border">↓</kbd> Navigate</span>
            <span><kbd className="font-mono bg-white px-1.5 py-0.5 rounded border">↵</kbd> Select</span>
            <span><kbd className="font-mono bg-white px-1.5 py-0.5 rounded border">esc</kbd> Dismiss</span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Ctrl+K Palette</span>
        </div>
      </div>
    </div>
  );
};
