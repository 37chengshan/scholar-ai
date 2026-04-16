/**
 * PDF Reference Chip Component
 *
 * Renders a clickable chip for PDF references in notes.
 * Syntax: [[pdf:paperId:page:5]]
 * On click: navigates to /read/:paperId?page=N
 *
 * Requirements: NOTE-02, D-13
 */

import { useNavigate } from 'react-router';
import { FileText } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/app/components/ui/tooltip';

interface PdfReferenceChipProps {
  paperId: string;
  page: number;
  children?: React.ReactNode;
}

export function PdfReferenceChip({ paperId, page, children }: PdfReferenceChipProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/read/${paperId}?page=${page}`);
  };

  const label = children || `P${page}`;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleClick}
            className="inline-flex items-center gap-1 bg-muted rounded-md px-2 py-0.5 text-sm hover:bg-accent/10 hover:text-accent cursor-pointer transition-colors"
          >
            <FileText className="w-3 h-3" />
            <span className="truncate max-w-[120px]">{label}</span>
            <span className="text-muted-foreground text-xs">p.{page}</span>
          </button>
        </TooltipTrigger>
        <TooltipContent>跳转到论文第 {page} 页</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Parse content text for PDF reference patterns and render chips.
 * Pattern: [[pdf:paperId:page:N]]
 *
 * Returns an array of React nodes (text segments + PdfReferenceChip components).
 */
export function parsePdfReferences(text: string): React.ReactNode[] {
  const pattern = /\[\[pdf:([^:]+):page:(\d+)\]\]/g;
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    // Add PDF reference chip
    const paperId = match[1];
    const page = parseInt(match[2], 10);
    nodes.push(
      <PdfReferenceChip key={`${paperId}-${page}-${match.index}`} paperId={paperId} page={page} />
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}
