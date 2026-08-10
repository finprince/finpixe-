import React, { useState, useRef, useEffect } from 'react';
import { httpClient } from '../../services/httpClient';

interface Message {
  id: string;
  sender: 'user' | 'kiki';
  text: string;
  timestamp: string;
  evidence_package?: {
    summary: string;
    domain: string;
    record_count: number;
    sample_records?: any[];
  };
  action_cards?: Array<{
    title: string;
    action_type: string;
    route: string;
  }>;
}

interface KikiPanelProps {
  onNavigate?: (page: string) => void;
}

export const KikiPanel: React.FC<KikiPanelProps> = ({ onNavigate }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome_1',
      sender: 'kiki',
      text: 'Good day! I am **KIKI 2027**, your local air-gapped AI Operating Assistant for FINPIXE ERP. How can I assist with your financial analytics, vouchers, or statutory compliance today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const quickQuestions = [
    "What were last week's sales?",
    "Show overdue invoices",
    "Why is GST mismatching?",
    "Take me to Inventory"
  ];

  // Session ID persistence across page navigation and refreshes
  const [sessionId] = useState<string>(() => {
    let sid = localStorage.getItem('kiki_session_id');
    if (!sid) {
      sid = `sess_web_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      localStorage.setItem('kiki_session_id', sid);
    }
    return sid;
  });

  const handleSendMessage = async (customText?: string) => {
    const textToSend = customText || inputMessage;
    if (!textToSend.trim() || isLoading) return;

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!customText) setInputMessage('');
    setIsLoading(true);

    try {
      const response = await httpClient.post('/api/v2/kiki/chat/', {
        message: textToSend,
        context_data: { session_id: sessionId }
      });

      const data = response;
      const kikiMsg: Message = {
        id: data.id || `kiki_${Date.now()}`,
        sender: 'kiki',
        text: data.reply || data.message || 'Processed request successfully.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        evidence_package: data.evidence_package,
        action_cards: data.action_cards
      };

      setMessages(prev => [...prev, kikiMsg]);
    } catch (err: any) {
      console.error("KIKI API Error:", err);
      const errorMsg: Message = {
        id: `err_${Date.now()}`,
        sender: 'kiki',
        text: "I experienced an error connecting to the KIKI AI Kernel. Please ensure the local Ollama/FINPIXE server is running.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating KIKI Launcher Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-orange-500 via-amber-500 to-indigo-600 text-white font-medium rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200 group"
        title="Open KIKI AI Operating Cockpit"
      >
        <div className="relative flex items-center justify-center w-7 h-7 bg-white/20 rounded-full">
          <span className="text-base animate-pulse">✨</span>
        </div>
        <span className="font-semibold text-sm tracking-wide">KIKI AI</span>
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
      </button>

      {/* Slide-over Drawer Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-black/40 backdrop-blur-xs transition-opacity duration-300">
          <div className="w-full max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full text-slate-100 animate-in slide-in-from-right duration-300">
            
            {/* Header */}
            <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-orange-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
                  K
                </div>
                <div>
                  <h2 className="font-bold text-slate-100 text-base leading-tight flex items-center gap-2">
                    KIKI 2027
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      Local AI Active
                    </span>
                  </h2>
                  <p className="text-xs text-slate-400">FINPIXE ERP Cognitive Operating Layer</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
              
              {/* Quick Suggestion Chips */}
              <div className="mb-4">
                <p className="text-xs font-medium text-slate-400 mb-2">Suggested Inquiries:</p>
                <div className="flex flex-wrap gap-1.5">
                  {quickQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 transition-colors text-left"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Message Thread */}
              {messages.map(msg => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-r from-orange-500 to-amber-600 text-white rounded-br-none'
                        : 'bg-slate-800 text-slate-200 border border-slate-700/60 rounded-bl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>

                    {/* Developer Debug Mode Evidence Package */}
                    {(window as any).__KIKI_DEBUG__ && msg.evidence_package && (
                      <div className="mt-3 p-3 rounded-xl bg-slate-900/80 border border-slate-700 text-xs space-y-2">
                        <div className="flex items-center justify-between text-amber-400 font-medium">
                          <span>📊 Debug Evidence Package</span>
                          <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/20 rounded">
                            {msg.evidence_package.record_count} Records
                          </span>
                        </div>
                        <p className="text-slate-300">{msg.evidence_package.summary}</p>
                      </div>
                    )}


                    {/* Interactive Action Cards */}
                    {msg.action_cards && msg.action_cards.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {msg.action_cards.map((card, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => {
                              if (onNavigate && card.route) {
                                const cleanRoute = card.route.replace('/', '').replace(/-/g, ' ');
                                onNavigate(cleanRoute);
                                setIsOpen(false);
                              }
                            }}
                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 shadow transition-colors"
                          >
                            <span>🚀</span> {card.title}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                </div>
              ))}

              {isLoading && (
                <div className="flex items-center gap-2 text-slate-400 text-xs p-2">
                  <div className="w-4 h-4 rounded-full border-2 border-orange-500 border-t-transparent animate-spin" />
                  <span>KIKI is processing intent & compiling evidence...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t border-slate-800 bg-slate-950">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask KIKI anything about vouchers, GST, sales, inventory..."
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isLoading}
                  className="px-4 py-2.5 bg-gradient-to-r from-orange-500 to-indigo-600 hover:from-orange-400 hover:to-indigo-500 disabled:opacity-50 text-white font-medium rounded-xl text-sm transition-all"
                >
                  Send
                </button>
              </form>
            </div>

          </div>
        </div>
      )}
    </>
  );
};
