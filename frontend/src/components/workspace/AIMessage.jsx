import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-gray-800 bg-[#1e1e1e] shadow-md">
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#252526] border-b border-gray-800 text-xs text-gray-400 font-mono select-none">
        <span className="font-semibold tracking-wide text-gray-300">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1.5 px-2 py-0.5 rounded text-gray-400 hover:text-white hover:bg-gray-700/60 transition-colors cursor-pointer text-xs"
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <Check size={13} className="text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy size={13} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="overflow-x-auto">
        <SyntaxHighlighter
          language={language || 'text'}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1rem',
            fontSize: '0.875rem',
            lineHeight: '1.55',
            backgroundColor: 'transparent',
          }}
          codeTagProps={{
            style: {
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            },
          }}
        >
          {value}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

export function AIMessage({ content }) {
  if (!content) return null;

  return (
    <div className="ai-message-content text-gray-900 text-[15px] leading-relaxed break-words space-y-1">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <div className="not-prose">{children}</div>;
          },
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const rawString = String(children).replace(/\n$/, '');
            const isMultiline = rawString.includes('\n');

            // If it has a language specifier or is multiline, render the styled CodeBlock
            if (match || isMultiline) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  value={rawString}
                />
              );
            }

            // Inline code styling
            return (
              <code
                className="bg-gray-100 text-pink-600 font-mono text-[0.875em] px-1.5 py-0.5 rounded border border-gray-200/80 font-medium"
                {...props}
              >
                {children}
              </code>
            );
          },
          p({ children }) {
            return <p className="mb-3 last:mb-0 leading-relaxed text-gray-800">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-gray-950">{children}</strong>;
          },
          h1({ children }) {
            return <h1 className="text-xl font-bold text-gray-950 mt-4 mb-2 first:mt-0 tracking-tight">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-lg font-bold text-gray-950 mt-3.5 mb-2 first:mt-0 tracking-tight">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold text-gray-950 mt-3 mb-1.5 first:mt-0">{children}</h3>;
          },
          ul({ children }) {
            return <ul className="list-disc pl-5 my-2.5 space-y-1.5 text-gray-800">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal pl-5 my-2.5 space-y-1.5 text-gray-800">{children}</ol>;
          },
          li({ children }) {
            return <li className="leading-relaxed">{children}</li>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-blue-500 bg-blue-50/50 pl-4 py-2 my-3 text-gray-700 italic rounded-r">
                {children}
              </blockquote>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3 border border-gray-200 rounded-lg shadow-xs">
                <table className="min-w-full divide-y divide-gray-200 text-sm text-left">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-50 text-gray-700 font-semibold">{children}</thead>;
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-gray-200 bg-white">{children}</tbody>;
          },
          th({ children }) {
            return <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600">{children}</th>;
          },
          td({ children }) {
            return <td className="px-3 py-2 text-gray-800">{children}</td>;
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline font-medium transition-colors"
              >
                {children}
              </a>
            );
          },
          hr() {
            return <hr className="my-4 border-gray-200" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default AIMessage;
