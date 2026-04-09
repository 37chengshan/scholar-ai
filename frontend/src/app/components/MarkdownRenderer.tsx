/**
 * MarkdownRenderer Component
 *
 * Renders markdown content with GFM tables, code block highlighting,
 * and custom component overrides. Replaces TypingText per D-01.
 *
 * Features:
 * - react-markdown with remarkGfm (tables, strikethrough, task lists)
 * - rehypeHighlight for code block syntax highlighting
 * - Custom CodeBlock component for fenced code blocks
 * - External links open in new tab
 * - Responsive tables with horizontal scroll
 * - Typography per UI-SPEC: text-sm leading-relaxed, --font-sans
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeMermaid from 'rehype-mermaid';
import 'katex/dist/katex.min.css';
import { clsx } from 'clsx';

import { CodeBlock } from './CodeBlock';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={clsx(
      'text-sm leading-relaxed',
      'font-[var(--font-sans)]',
      className
    )}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeHighlight, rehypeMermaid]}
        components={{
        // Mermaid diagram container styling
        pre({ children }) {
          return <div className="my-4 overflow-x-auto">{children}</div>;
        },

        // Fenced code blocks → CodeBlock, inline code → <code>
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const isBlock = match && String(children).includes('\n');

          if (isBlock) {
            return (
              <CodeBlock
                code={String(children).replace(/\n$/, '')}
                language={match[1]}
              />
            );
          }

          return (
            <code
              className="bg-muted px-1.5 py-0.5 rounded font-mono text-xs"
              {...props}
            >
              {children}
            </code>
          );
        },

        // External links open in new tab
        a({ href, children, ...props }) {
          const isExternal = href?.startsWith('http');
          return (
            <a
              href={href}
              target={isExternal ? '_blank' : undefined}
              rel={isExternal ? 'noopener noreferrer' : undefined}
              className="text-[#d35400] hover:underline transition-colors"
              {...props}
            >
              {children}
            </a>
          );
        },

        // Responsive tables
        table({ children, ...props }) {
          return (
            <div className="my-3 overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-sm" {...props}>
                {children}
              </table>
            </div>
          );
        },

        // Table header styling
        th({ children, ...props }) {
          return (
            <th
              className="bg-muted px-3 py-2 text-left font-semibold border-b border-border/50"
              {...props}
            >
              {children}
            </th>
          );
        },

        // Table cell styling
        td({ children, ...props }) {
          return (
            <td className="px-3 py-2 border-b border-border/50" {...props}>
              {children}
            </td>
          );
        },

        // Headings with serif font per UI-SPEC
        h1({ children, ...props }) {
          return (
            <h1
              className="text-lg font-semibold font-[var(--font-serif)] mt-4 mb-2"
              {...props}
            >
              {children}
            </h1>
          );
        },
        h2({ children, ...props }) {
          return (
            <h2
              className="text-base font-semibold font-[var(--font-serif)] mt-3 mb-2"
              {...props}
            >
              {children}
            </h2>
          );
        },
        h3({ children, ...props }) {
          return (
            <h3
              className="text-sm font-semibold mt-3 mb-1.5"
              {...props}
            >
              {children}
            </h3>
          );
        },

        // Lists
        ul({ children, ...props }) {
          return (
            <ul className="list-disc ml-5 my-2 space-y-1" {...props}>
              {children}
            </ul>
          );
        },
        ol({ children, ...props }) {
          return (
            <ol className="list-decimal ml-5 my-2 space-y-1" {...props}>
              {children}
            </ol>
          );
        },

        // Blockquotes
        blockquote({ children, ...props }) {
          return (
            <blockquote
              className="border-l-4 border-muted-foreground/30 pl-4 italic text-muted-foreground my-2"
              {...props}
            >
              {children}
            </blockquote>
          );
        },

        // Horizontal rule
        hr() {
          return <hr className="my-4 border-border" />;
        },

        // Paragraphs
        p({ children, ...props }) {
          return (
            <p className="my-2" {...props}>
              {children}
            </p>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  );
}
