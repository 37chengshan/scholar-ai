/**
 * TypingText Component
 *
 * Pretext-style typing effect with real-time Markdown parsing.
 * Streams at 30-50 chars/sec with blinking cursor.
 *
 * Part of Agent-Native architecture (D-18)
 */

import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx } from 'clsx';

/**
 * TypingText props
 */
export interface TypingTextProps {
  text: string;
  speed?: number; // chars per second (30-50 per D-18)
  onComplete?: () => void;
  className?: string;
  enableMarkdown?: boolean;
}

/**
 * Simple Markdown to HTML converter
 * For full Markdown support with LaTeX, install:
 * npm install react-markdown remark-gfm remark-math rehype-katex katex
 */
function simpleMarkdownToHtml(text: string): string {
  return text
    // Escape HTML entities first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Headers
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-semibold mt-4 mb-2">$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre class="bg-muted p-3 rounded-sm font-mono text-xs overflow-x-auto my-3"><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded font-mono text-xs">$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')
    // Unordered lists
    .replace(/^[\-\*] (.+)$/gim, '<li class="ml-4 list-disc">$1</li>')
    // Ordered lists
    .replace(/^\d+\. (.+)$/gim, '<li class="ml-4 list-decimal">$1</li>')
    // Blockquotes
    .replace(/^&gt; (.+)$/gim, '<blockquote class="border-l-4 border-muted-foreground/30 pl-4 italic text-muted-foreground">$1</blockquote>')
    // Horizontal rules
    .replace(/^---$/gim, '<hr class="my-4 border-border" />')
    // Line breaks (preserve paragraphs)
    .replace(/\n\n/g, '</p><p class="my-2">')
    .replace(/\n/g, '<br>');
}

/**
 * TypingText Component
 *
 * Displays text with a typing effect and optional Markdown rendering.
 * Uses debouncing (100ms) for performance during rapid updates.
 */
export function TypingText({
  text,
  speed = 40, // 30-50 chars/sec per D-18
  onComplete,
  className,
  enableMarkdown = true,
}: TypingTextProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const indexRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [parsedHtml, setParsedHtml] = useState('');

  // Calculate interval in ms (e.g., 40 chars/sec = 25ms per char)
  const intervalMs = useMemo(() => 1000 / speed, [speed]);

  // Typing effect
  useEffect(() => {
    // Reset when text changes
    if (displayedText.length > text.length) {
      setDisplayedText('');
      indexRef.current = 0;
      setIsComplete(false);
    }

    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Start typing
    intervalRef.current = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayedText(prev => prev + text[indexRef.current]);
        indexRef.current++;
      } else {
        // Typing complete
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        setIsComplete(true);
        onComplete?.();
      }
    }, intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [text, intervalMs, onComplete, displayedText.length]);

  // Debounced Markdown parsing (100ms per RESEARCH.md)
  useEffect(() => {
    if (!enableMarkdown) {
      setParsedHtml(displayedText);
      return;
    }

    // Clear existing debounce timer
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Debounce parsing
    debounceRef.current = setTimeout(() => {
      try {
        const html = simpleMarkdownToHtml(displayedText);
        setParsedHtml(html);
      } catch (error) {
        // Fallback to raw text on error
        console.error('Markdown parsing error:', error);
        setParsedHtml(displayedText);
      }
    }, 100);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [displayedText, enableMarkdown]);

  return (
    <div className={clsx('relative', className)}>
      {/* Typing cursor */}
      <AnimatePresence>
        {!isComplete && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="inline-block w-0.5 h-4 bg-primary ml-0.5 animate-pulse"
            style={{
              animation: 'blink 0.8s ease-in-out infinite',
            }}
          />
        )}
      </AnimatePresence>

      {/* Rendered content */}
      {enableMarkdown ? (
        <div
          className="prose prose-sm max-w-none text-foreground"
          dangerouslySetInnerHTML={{ __html: parsedHtml }}
        />
      ) : (
        <span className="whitespace-pre-wrap">{displayedText}</span>
      )}

      {/* CSS for blinking cursor */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

export type { TypingTextProps as TypingTextPropsType };