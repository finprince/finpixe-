import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Search, BookOpen, FileText, CheckCircle2, ShieldCheck } from 'lucide-react';

interface KnowledgeStats {
  collection_name: string;
  knowledge_directory: string;
  total_chunks_indexed: number;
  persist_directory: string;
  status: string;
}

interface SearchResultItem {
  chunk_id: string;
  text: string;
  metadata: {
    filename: string;
    category: string;
    page_number: number;
    section_heading: string;
  };
  confidence: number;
}

export const DeveloperKnowledge: React.FC = () => {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [reindexing, setReindexing] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/kiki/rag/stats/');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Error fetching RAG stats:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async (rebuild: boolean = false) => {
    setReindexing(true);
    setNotice(rebuild ? 'Rebuilding global collection from scratch...' : 'Scanning & indexing knowledge repository...');
    try {
      const res = await fetch('/api/kiki/rag/reindex/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rebuild })
      });
      if (res.ok) {
        const data = await res.json();
        setNotice(`Successfully indexed ${data.total_chunks} chunks across ${data.total_documents} documents in ${data.execution_time_seconds}s.`);
        fetchStats();
      }
    } catch (e) {
      setNotice('Error executing reindex.');
    } finally {
      setReindexing(false);
    }
  };

  const handleSearchDiagnostic = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch('/api/kiki/rag/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery })
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error('Search error:', e);
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-orange-500 to-amber-600 rounded-lg shadow-lg">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Developer Knowledge Library</h1>
              <p className="text-xs text-slate-400">FINPIXE Air-Gapped Global Knowledge Base & Local ChromaDB Vector Store</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleReindex(false)}
            disabled={reindexing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${reindexing ? 'animate-spin' : ''}`} />
            Scan & Index Knowledge
          </button>

          <button
            onClick={() => handleReindex(true)}
            disabled={reindexing}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-xs font-semibold text-white rounded-lg shadow-md transition"
          >
            <RefreshCw className={`w-4 h-4 ${reindexing ? 'animate-spin' : ''}`} />
            Rebuild Global Collection
          </button>
        </div>
      </div>

      {notice && (
        <div className="p-3 bg-orange-950/60 border border-orange-700/50 rounded-lg text-xs text-orange-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-orange-400 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Target Collection</span>
          <p className="text-sm font-bold font-mono text-orange-400">{stats?.collection_name || 'finpixe_global_knowledge'}</p>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Total Chunks Indexed</span>
          <p className="text-2xl font-bold text-slate-100">{loading ? '...' : stats?.total_chunks_indexed || 0}</p>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Security Scope</span>
          <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold pt-1">
            <ShieldCheck className="w-4 h-4" />
            <span>Developer-Managed Global</span>
          </div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">ChromaDB Status</span>
          <div className="flex items-center gap-2 pt-1">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-slate-200">LOCAL PERSISTENT ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Developer Knowledge Folder Topology */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-orange-400" />
            Repository Categories (`backend/core/kiki/knowledge/`)
          </h2>
          <span className="text-xs text-slate-400">PDF • DOCX • TXT • MD • CSV • HTML</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
          {['GST', 'Accounting', 'Finance', 'Payroll', 'HR', 'Manuals', 'FAQ', 'Training', 'SOP', 'Tax', 'Policies'].map((cat) => (
            <div key={cat} className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-300 flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-amber-500" />
              <span>{cat}/</span>
            </div>
          ))}
        </div>
      </div>

      {/* Search Diagnostic Tester */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
        <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
          <Search className="w-4 h-4 text-orange-400" />
          Developer Vector Search Diagnostic Tester
        </h2>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Type a test query e.g. 'What is Input Tax Credit?' or 'leave policy'..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearchDiagnostic()}
            className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500"
          />
          <button
            onClick={handleSearchDiagnostic}
            disabled={searching}
            className="px-4 py-2.5 bg-orange-600 hover:bg-orange-500 font-semibold text-xs text-white rounded-lg transition"
          >
            {searching ? 'Searching...' : 'Run Vector Search'}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-bold text-slate-400">Top Retrieved Vector Chunks (`finpixe_global_knowledge`):</h3>
            <div className="space-y-2">
              {searchResults.map((res, idx) => (
                <div key={idx} className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
                  <div className="flex items-center justify-between text-orange-400 font-semibold">
                    <span>[{idx + 1}] {res.metadata.filename} (Page {res.metadata.page_number}, Section: {res.metadata.section_heading})</span>
                    <span className="text-slate-400 font-mono">Confidence: {(res.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <p className="text-slate-300 font-mono text-[11px] leading-relaxed">{res.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default DeveloperKnowledge;
