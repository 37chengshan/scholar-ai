/**
 * ToolCallDisplay Component
 *
 * Displays individual tool execution with:
 * - Tool name and parameters
 * - Execution status (pending, running, success, error)
 * - Result preview with expand/collapse
 * - Timing information
 *
 * Part of Agent-Native architecture (D-06)
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Wrench,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  ExternalLink,
} from 'lucide-react';
import { clsx } from 'clsx';

export type ToolStatus = 'pending' | 'running' | 'success' | 'error';

export interface ToolCallData {
  tool: string;
  params?: Record<string, any>;
  result?: any;
  error?: string;
  status: ToolStatus;
  timestamp?: string;
  duration?: number;
  tokensUsed?: number;
}

export interface ToolCallDisplayProps {
  toolCall: ToolCallData;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  className?: string;
}

const TOOL_ICONS: Record<string, string> = {
  external_search: 'search',
  rag_search: 'search',
  list_papers: 'folder',
  read_paper: 'file-text',
  create_note: 'edit',
  update_note: 'edit',
  upload_paper: 'upload',
  delete_paper: 'trash',
  extract_references: 'link',
  merge_documents: 'merge',
};

const TOOL_LABELS: Record<string, string> = {
  external_search: 'External Search',
  rag_search: 'RAG Search',
  list_papers: 'List Papers',
  read_paper: 'Read Paper',
  create_note: 'Create Note',
  update_note: 'Update Note',
  upload_paper: 'Upload Paper',
  delete_paper: 'Delete Paper',
  extract_references: 'Extract References',
  merge_documents: 'Merge Documents',
  execute_command: 'Execute Command',
  ask_user_confirmation: 'Ask Confirmation',
  show_message: 'Show Message',
};

function getStatusIcon(status: ToolStatus) {
  switch (status) {
    case 'pending':
      return Clock;
    case 'running':
      return Loader2;
    case 'success':
      return CheckCircle2;
    case 'error':
      return AlertCircle;
  }
}

function getStatusColor(status: ToolStatus) {
  switch (status) {
    case 'pending':
      return 'text-muted-foreground bg-muted/50';
    case 'running':
      return 'text-primary bg-primary/10';
    case 'success':
      return 'text-green-600 bg-green-50';
    case 'error':
      return 'text-destructive bg-destructive/10';
  }
}

export function ToolCallDisplay({
  toolCall,
  isExpanded = false,
  onToggleExpand,
  className,
}: ToolCallDisplayProps) {
  const [localExpanded, setLocalExpanded] = useState(isExpanded);
  
  const expanded = onToggleExpand ? isExpanded : localExpanded;
  const toggleExpand = onToggleExpand || (() => setLocalExpanded(!localExpanded));
  
  const Icon = getStatusIcon(toolCall.status);
  const statusColor = getStatusColor(toolCall.status);
  const toolLabel = TOOL_LABELS[toolCall.tool] || toolCall.tool;
  
  const hasResult = toolCall.result !== undefined || toolCall.error !== undefined;
  const isRunning = toolCall.status === 'running';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'border border-border/50 rounded-sm overflow-hidden',
        toolCall.status === 'error' && 'border-destructive/30',
        className
      )}
    >
      <button
        onClick={hasResult ? toggleExpand : undefined}
        disabled={!hasResult}
        className={clsx(
          'w-full px-3 py-2.5 flex items-center gap-2.5 transition-colors',
          hasResult && 'cursor-pointer hover:bg-muted/50',
          !hasResult && 'cursor-default'
        )}
      >
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', statusColor)}>
          <Icon className={clsx('w-3.5 h-3.5', isRunning && 'animate-spin')} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Wrench className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span className="font-medium text-sm truncate">{toolLabel}</span>
          </div>
          
          {toolCall.params && Object.keys(toolCall.params).length > 0 && (
            <div className="text-xs text-muted-foreground truncate mt-0.5">
              {Object.entries(toolCall.params)
                .slice(0, 2)
                .map(([k, v]) => `${k}: ${typeof v === 'string' ? v.substring(0, 30) : JSON.stringify(v).substring(0, 30)}`)
                .join(', ')}
            </div>
          )}
        </div>
        
        {toolCall.duration && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            {(toolCall.duration / 1000).toFixed(1)}s
          </div>
        )}
        
        {toolCall.tokensUsed && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Zap className="w-3 h-3" />
            {toolCall.tokensUsed}t
          </div>
        )}
        
        {hasResult && (
          <div className="flex-shrink-0">
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </div>
        )}
      </button>
      
      <AnimatePresence>
        {expanded && hasResult && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="border-t border-border/50 bg-muted/30"
          >
            <div className="px-3 py-2.5 text-xs">
              {toolCall.error ? (
                <div className="text-destructive font-medium">{toolCall.error}</div>
              ) : toolCall.result ? (
                <div className="space-y-2">
                  {typeof toolCall.result === 'object' ? (
                    <>
                      {toolCall.result.success !== undefined && (
                        <div className={clsx(
                          'font-medium',
                          toolCall.result.success ? 'text-green-600' : 'text-destructive'
                        )}>
                          Status: {toolCall.result.success ? 'Success' : 'Failed'}
                        </div>
                      )}
                      
                      {toolCall.result.sources && Array.isArray(toolCall.result.sources) && (
                        <div>
                          <span className="text-muted-foreground">Sources: </span>
                          <span className="font-medium">{toolCall.result.sources.length} papers</span>
                        </div>
                      )}
                      
                      {toolCall.result.papers && Array.isArray(toolCall.result.papers) && (
                        <div>
                          <span className="text-muted-foreground">Found: </span>
                          <span className="font-medium">{toolCall.result.papers.length} papers</span>
                        </div>
                      )}
                      
                      {toolCall.result.message && (
                        <div className="text-muted-foreground">{toolCall.result.message}</div>
                      )}
                      
                      {toolCall.result.data && (
                        <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-32">
                          {JSON.stringify(toolCall.result.data, null, 2)}
                        </pre>
                      )}
                    </>
                  ) : (
                    <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-32">
                      {JSON.stringify(toolCall.result, null, 2)}
                    </pre>
                  )}
                </div>
              ) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export type { ToolCallDisplayProps as ToolCallDisplayPropsType };