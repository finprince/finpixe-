import React from 'react';

interface KikiMarkdownProps {
  content: string;
  isUser?: boolean;
}

/**
 * Renders inline markdown: bold (**text**), italics (*text*), code (`code`), and currency symbols (₹).
 */
export const renderInline = (text: string): React.ReactNode => {
  if (!text) return null;

  // Split by bold (**...**), code (`...`), and italic (*...*)
  const parts = text.split(/(\*\*.*?\*\*|`.*?`|\*.*?\*)/g);

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-slate-950 text-amber-300 font-mono text-xs border border-slate-800"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2 && !part.startsWith('**')) {
      return (
        <em key={idx} className="italic text-slate-300">
          {part.slice(1, -1)}
        </em>
      );
    }
    return <span key={idx}>{part}</span>;
  });
};

/**
 * Structured Markdown and Table Renderer for KIKI responses.
 */
export const KikiMarkdown: React.FC<KikiMarkdownProps> = ({ content, isUser = false }) => {
  if (isUser) {
    return <p className="whitespace-pre-wrap leading-relaxed">{content}</p>;
  }

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Markdown Table Detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && i + 1 < lines.length && lines[i + 1].includes('---')) {
      const headerLine = trimmed;
      const headers = headerLine
        .slice(1, -1)
        .split('|')
        .map(h => h.trim());

      i += 2; // Skip header and separator (---) line

      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const rowCells = lines[i]
          .trim()
          .slice(1, -1)
          .split('|')
          .map(c => c.trim());
        rows.push(rowCells);
        i++;
      }

      elements.push(
        <div
          key={`table_${i}`}
          className="my-3 overflow-x-auto rounded-xl border border-slate-700/80 bg-slate-900/90 shadow-md scrollbar-thin scrollbar-thumb-slate-700"
        >
          <table className="w-full text-xs text-left text-slate-200 border-collapse">
            <thead className="bg-slate-800/95 text-amber-400 font-semibold border-b border-slate-700 text-[11px] uppercase tracking-wider sticky top-0">
              <tr>
                {headers.map((h, hIdx) => (
                  <th key={hIdx} className="px-3 py-2.5 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className={`hover:bg-slate-800/60 transition-colors ${
                    rIdx % 2 === 0 ? 'bg-slate-900/40' : 'bg-slate-900/80'
                  }`}
                >
                  {row.map((cell, cIdx) => {
                    const isCurrency = cell.startsWith('₹') || cell.startsWith('-₹');
                    return (
                      <td
                        key={cIdx}
                        className={`px-3 py-2 whitespace-nowrap ${
                          isCurrency ? 'font-medium text-amber-300' : 'text-slate-300'
                        }`}
                      >
                        {renderInline(cell)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 2. Headings
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h3_${i}`} className="font-bold text-amber-400 text-xs tracking-wider uppercase mt-3.5 mb-1.5 flex items-center gap-1.5">
          <span>▸</span>
          <span>{renderInline(trimmed.slice(4))}</span>
        </h4>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h2_${i}`} className="font-bold text-amber-300 text-sm mt-3.5 mb-1.5">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={`h1_${i}`} className="font-extrabold text-amber-200 text-base mt-4 mb-2">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      i++;
      continue;
    }

    // 3. Bullet List Items (- or * or •)
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
      const itemText = trimmed.slice(2);
      elements.push(
        <div key={`li_${i}`} className="flex items-start gap-2 my-1 text-slate-200 text-xs leading-relaxed pl-1">
          <span className="text-amber-400 font-bold leading-none mt-0.5">•</span>
          <span className="flex-1">{renderInline(itemText)}</span>
        </div>
      );
      i++;
      continue;
    }

    // 4. Blank lines
    if (trimmed === '') {
      elements.push(<div key={`blank_${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // 5. Standard paragraph text
    elements.push(
      <p key={`p_${i}`} className="my-1 text-xs text-slate-200 leading-relaxed">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
};
