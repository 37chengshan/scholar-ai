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
import { simpleMarkdownToHtml } from '../../lib/markdown-utils';

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
  const intervalMs = useMemo(() => Math.max(16, 1000 / speed), [speed]);

  // Typing effect
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Reset when the target text shrinks or is replaced from scratch.
    if (text.length < indexRef.current) {
      indexRef.current = 0;
      setDisplayedText('');
      setIsComplete(false);
    }

    if (text.length === 0) {
      setDisplayedText('');
      setIsComplete(true);
      return;
    }

    // Keep the visible text aligned with the currently revealed prefix.
    setDisplayedText(text.slice(0, indexRef.current));
    setIsComplete(indexRef.current >= text.length);

    // Clear any existing interval.
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = setInterval(() => {
      if (indexRef.current < text.length) {
        indexRef.current += 1;
        setDisplayedText(text.slice(0, indexRef.current));
        setIsComplete(indexRef.current >= text.length);
      } else {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setIsComplete(true);
        onComplete?.();
      }
    }, intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [text, intervalMs, onComplete]);

  const parsedHtml = useMemo(() => {
    if (!enableMarkdown || !isComplete) {
      return '';
    }

    try {
      return simpleMarkdownToHtml(displayedText);
    } catch (error) {
      console.error('Markdown parsing error:', error);
      return displayedText;
    }
  }, [displayedText, enableMarkdown, isComplete]);

  return (
    <div className={clsx('relative flex items-start gap-1', className)}>
      {/* Rendered content */}
      {enableMarkdown && isComplete ? (
        <div
          className="prose prose-sm max-w-none text-foreground whitespace-pre-wrap editorial-reading-surface font-serif"
          dangerouslySetInnerHTML={{ __html: parsedHtml }}
        />
      ) : (
        <span className="whitespace-pre-wrap">{displayedText}</span>
      )}

      {/* Typing cursor */}
      <AnimatePresence>
        {!isComplete && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-1 inline-block w-0.5 h-4 bg-primary shrink-0 animate-pulse"
            style={{
              animation: 'blink 0.8s ease-in-out infinite',
            }}
          />
        )}
      </AnimatePresence>

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
