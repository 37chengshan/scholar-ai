/**
 * CodeBlock Component
 *
 * Syntax-highlighted code block with copy button.
 * Used by MarkdownRenderer for fenced code blocks.
 *
 * Features:
 * - highlight.js syntax highlighting via rehype-highlight
 * - Language badge in top-right corner
 * - Copy button with 2s "Copied!" feedback
 * - Dark background, scrollable overflow
 */

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = code;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const displayLanguage = language || 'text';

  return (
    <div className="relative my-3 overflow-hidden bg-[var(--color-paper-2)] border border-border/50 text-foreground magazine-code">
      {/* Header with language badge and copy button */}
      <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-border/50 bg-muted/40">
        <span className="text-xs font-mono text-gray-400 lowercase">
          {displayLanguage}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
          aria-label={copied ? 'Copied!' : 'Copy code'}
        >
          <AnimatePresence mode="wait">
            {copied ? (
              <motion.span
                key="check"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="inline-flex items-center gap-1 text-green-400"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Copied!</span>
              </motion.span>
            ) : (
              <motion.span
                key="copy"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="inline-flex items-center gap-1"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>

      {/* Code content */}
      <pre className="p-4 overflow-x-auto">
        <code className={`language-${displayLanguage} font-mono text-sm leading-relaxed`}>
          {code}
        </code>
      </pre>
    </div>
  );
}
