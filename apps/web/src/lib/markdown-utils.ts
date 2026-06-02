/**
 * Shared Markdown-to-HTML utility with XSS-safe escape-first strategy.
 *
 * Usage:
 *   import { simpleMarkdownToHtml } from '@/lib/markdown-utils';
 *   dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(userInput) }}
 *
 * Security: HTML entities (&, <, >) are escaped BEFORE any Markdown
 * replacement runs, preventing script injection through crafted input.
 * Links are filtered to block javascript: and data: URI schemes.
 */

/** Schemes allowed in link hrefs. Everything else is stripped. */
const SAFE_SCHEME_RE = /^(https?|mailto):/i;

/** Dangerous schemes that must never appear in link hrefs. */
const DANGEROUS_SCHEME_RE = /^(javascript|data|vbscript):/i;

/**
 * Escape HTML entities to prevent XSS.
 * Must run BEFORE any Markdown-to-HTML conversion.
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

/**
 * Convert a safe URL for use in an href attribute.
 * Returns the URL if it uses an allowed scheme, otherwise returns '#'.
 */
function sanitizeUrl(url: string): string {
  const trimmed = url.trim();
  // Relative URLs and fragment-only are safe
  if (trimmed.startsWith('#') || trimmed.startsWith('/')) {
    return trimmed;
  }
  // Block dangerous schemes
  if (DANGEROUS_SCHEME_RE.test(trimmed)) {
    return '#';
  }
  // Allow safe schemes
  if (SAFE_SCHEME_RE.test(trimmed)) {
    return trimmed;
  }
  // Protocol-relative URLs (//example.com) are allowed
  if (trimmed.startsWith('//')) {
    return trimmed;
  }
  // Default: block unknown schemes
  return '#';
}

/**
 * Simple Markdown-to-HTML converter with XSS protection.
 *
 * Converts basic Markdown syntax to HTML. For full Markdown support
 * (tables, GFM, etc.), use react-markdown instead.
 *
 * @param text - Raw user input (may contain Markdown)
 * @returns Safe HTML string
 */
export function simpleMarkdownToHtml(text: string): string {
  // Step 1: Escape HTML entities BEFORE any Markdown processing
  let html = escapeHtml(text);

  // Step 2: Apply Markdown transformations on escaped text
  html = html
    // Headers
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-semibold mt-4 mb-2">$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Code blocks (fenced)
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre class="bg-muted p-3 rounded-sm font-mono text-xs overflow-x-auto my-3"><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded font-mono text-xs">$1</code>')
    // Links -- with javascript:/data: scheme filtering
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      (_match, linkText: string, rawUrl: string) => {
        const safeUrl = sanitizeUrl(rawUrl);
        return `<a href="${safeUrl}" class="text-primary hover:underline" target="_blank" rel="noopener noreferrer">${linkText}</a>`;
      },
    )
    // Unordered lists
    .replace(/^[-*] (.+)$/gim, '<li class="ml-4 list-disc">$1</li>')
    // Ordered lists
    .replace(/^\d+\. (.+)$/gim, '<li class="ml-4 list-decimal">$1</li>')
    // Blockquotes (note: > is already escaped to &gt;)
    .replace(/^&gt; (.+)$/gim, '<blockquote class="border-l-4 border-muted-foreground/30 pl-4 italic text-muted-foreground">$1</blockquote>')
    // Horizontal rules
    .replace(/^---$/gim, '<hr class="my-4 border-border" />')
    // Paragraph breaks
    .replace(/\n\n/g, '</p><p class="my-2">')
    // Line breaks
    .replace(/\n/g, '<br>');

  return html;
}
