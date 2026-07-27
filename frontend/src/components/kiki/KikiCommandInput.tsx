import React, { useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface KikiCommandInputProps {
  input: string;
  onChange: (value: string) => void;
  onSend: (text?: string) => void;
  isLoading: boolean;
  useGrounding?: boolean;
  onToggleGrounding?: () => void;
}

export const KikiCommandInput: React.FC<KikiCommandInputProps> = ({
  input,
  onChange,
  onSend,
  isLoading
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 110)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSend();
      }
    }
  };

  return (
    <div className="p-3 bg-white dark:bg-slate-900 border-t border-[#E5E7EB] dark:border-slate-800 shrink-0">
      {/* Clean Floating Command Bar Input */}
      <div className="relative flex items-center min-h-[48px] bg-slate-50/90 dark:bg-slate-800/90 border border-[#E5E7EB] dark:border-slate-700/80 rounded-2xl focus-within:border-[#FF8A00] focus-within:ring-2 focus-within:ring-[#FF8A00]/20 transition-all px-3 py-1.5 shadow-2xs">
        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Kiki anything..."
          rows={1}
          disabled={isLoading}
          className="flex-1 px-1 py-1 text-xs bg-transparent border-none outline-none focus:outline-none resize-none text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 max-h-24 leading-relaxed"
        />

        {/* Right Send Button */}
        <div className="shrink-0 pl-2">
          <button
            type="button"
            onClick={() => onSend()}
            disabled={isLoading || !input.trim()}
            className="p-2 bg-[#FF8A00] text-white rounded-xl disabled:opacity-40 hover:bg-[#e07a00] transition-all shadow-xs shrink-0 cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
