/**
 * AgentActivityPanel Component
 *
 * Right sidebar panel for Chat page showing:
 * - Tool call history (reasoning, tool_call, tool_result events)
 * - Token consumption statistics
 * - Cost estimation
 * - Execution timeline
 *
 * Part of Agent-Native architecture (D-06, D-07)
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Activity,
  Zap,
  DollarSign,
  Clock,
  ChevronDown,
  ChevronUp,
  Brain,
  Wrench,
  FileText,
  Settings,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { clsx } from 'clsx';
import { SSEEvent } from '@/services/sseService';
import { ToolCallDisplay, ToolCallData, ToolStatus } from './ToolCallDisplay';

export interface AgentActivityPanelProps {
  events: SSEEvent[];
  tokensUsed?: number;
  cost?: number;
  totalTime?: number;
  className?: string;
  isStreaming?: boolean;
  monthlyTokenUsage?: {
    totalTokens: number;
    totalCostCny: number;
    requestCount: number;
  };
}

interface ActivityStats {
  totalTools: number;
  successfulTools: number;
  failedTools: number;
  totalTokens: number;
  estimatedCost: number;
  totalTime: number;
  thoughts: number;
}

function calculateStats(events: SSEEvent[]): ActivityStats {
  const stats: ActivityStats = {
    totalTools: 0,
    successfulTools: 0,
    failedTools: 0,
    totalTokens: 0,
    estimatedCost: 0,
    totalTime: 0,
    thoughts: 0,
  };
  
  events.forEach(event => {
    if (event.type === 'tool_call') {
      stats.totalTools++;
    }
    if (event.type === 'tool_result') {
      // Check success field in result
      if (event.result?.success === true) {
        stats.successfulTools++;
      } else if (event.result?.success === false || event.result?.error) {
        stats.failedTools++;
      }
      if (event.result?.tokensUsed) stats.totalTokens += event.result.tokensUsed;
      if (event.result?.duration) stats.totalTime += event.result.duration;
    }
    if (event.type === 'reasoning') {
      stats.thoughts++;
    }
  });
  
  stats.estimatedCost = (stats.totalTokens / 1000) * 0.002;
  
  return stats;
}

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

// Animated number component for real-time effect
function AnimatedNumber({ 
  value, 
  isStreaming,
  suffix = '',
  prefix = '',
  decimals = 0 
}: { 
  value: number; 
  isStreaming: boolean;
  suffix?: string;
  prefix?: string;
  decimals?: number;
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const animationRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  
  useEffect(() => {
    if (isStreaming) {
      // Animate incrementally
      const duration = 2000; // 2 seconds
      const startValue = displayValue;
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        
        const current = startValue + (value - startValue) * easeOut;
        setDisplayValue(current);
        
        if (progress < 1) {
          animationRef.current = setTimeout(animate, 50);
        }
      };
      
      animate();
    } else {
      // Show final value immediately
      setDisplayValue(value);
    }
    
    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, [value, isStreaming]);
  
  return (
    <span className="tabular-nums">
      {prefix}{displayValue.toFixed(decimals)}{suffix}
    </span>
  );
}

export function AgentActivityPanel({ 
  events, 
  tokensUsed = 0, 
  cost = 0, 
  totalTime = 0, 
  className,
  isStreaming = false,
  monthlyTokenUsage,
}: AgentActivityPanelProps) {
  const [showTools, setShowTools] = useState(true);
  const [showThoughts, setShowThoughts] = useState(true);
  
  const stats = useMemo(() => {
    const baseStats = calculateStats(events);
    // Use actual tokens, cost, and time from API if available
    return {
      ...baseStats,
      totalTokens: tokensUsed || baseStats.totalTokens,
      estimatedCost: cost || baseStats.estimatedCost,
      totalTime: totalTime || baseStats.totalTime
    };
  }, [events, tokensUsed, cost, totalTime]);
  
  const toolCalls = useMemo(() => {
    const calls: ToolCallData[] = [];
    const callMap = new Map<string, number>(); // Map tool name to index in calls array
    
    events.forEach((event, index) => {
      if (event.type === 'tool_call') {
        const call: ToolCallData = {
          tool: event.tool || 'unknown',
          params: event.content?.params || event.content,
          status: 'running',
          timestamp: event.timestamp,
        };
        calls.push(call);
        // Store index for later update from tool_result
        callMap.set(`${event.tool}-${index}`, calls.length - 1);
      }
      if (event.type === 'tool_result') {
        const key = event.tool || 'unknown';
        // Find the most recent running tool call with matching name
        let callIndex = -1;
        for (let i = calls.length - 1; i >= 0; i--) {
          if (calls[i].tool === key && calls[i].status === 'running') {
            callIndex = i;
            break;
          }
        }
        
        if (callIndex >= 0) {
          calls[callIndex].status = event.result?.success ? 'success' : 'error';
          calls[callIndex].result = event.result;
          calls[callIndex].error = event.result?.error;
          calls[callIndex].duration = event.result?.duration;
          calls[callIndex].tokensUsed = event.result?.tokensUsed;
        } else {
          // Standalone result without prior call
          calls.push({
            tool: key,
            status: event.result?.success ? 'success' : 'error',
            result: event.result,
            error: event.result?.error,
          });
        }
      }
    });
    
    return calls;
  }, [events]);
  
  const thoughts = useMemo(() => {
    return events.filter(e => e.type === 'reasoning').map(e => ({
      content: e.content,
      timestamp: e.timestamp,
    }));
  }, [events]);
  
  const hasActivity = toolCalls.length > 0 || thoughts.length > 0;
  
  return (
    <div
      className={clsx(
        'w-[320px] border-l border-border/50 bg-background flex flex-col h-full',
        className
      )}
    >
      <div className="px-4 py-3.5 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-sm font-bold tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Agent Activity
          </h3>
          <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded-sm">
            {toolCalls.length + thoughts.length}
          </span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {monthlyTokenUsage && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg p-3 border border-primary/20"
            >
              <div className="text-xs font-bold tracking-wide uppercase text-primary mb-2">
                历史累计
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-muted-foreground">总 Tokens</div>
                  <div className="font-mono font-bold text-lg text-primary">
                    {(monthlyTokenUsage.totalTokens / 1000).toFixed(1)}K
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">总费用</div>
                  <div className="font-mono font-bold text-lg text-green-600">
                    ¥{monthlyTokenUsage.totalCostCny.toFixed(2)}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-muted/50 rounded-lg p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground">
                当前回合
              </div>
              {isStreaming && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-1.5 text-xs text-primary"
                >
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>处理中</span>
                </motion.div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2">
                <Zap className={clsx("w-4 h-4", isStreaming ? "text-primary animate-pulse" : "text-primary")} />
                <div>
                  <div className="text-xs text-muted-foreground">Tokens</div>
                  <div className="font-mono font-medium text-sm">
                    <AnimatedNumber 
                      value={tokensUsed} 
                      isStreaming={isStreaming}
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <DollarSign className={clsx("w-4 h-4", isStreaming ? "text-green-600 animate-pulse" : "text-green-600")} />
                <div>
                  <div className="text-xs text-muted-foreground">Cost</div>
                  <div className="font-mono font-medium text-sm">
                    <AnimatedNumber 
                      value={cost} 
                      isStreaming={isStreaming}
                      prefix="$"
                      decimals={4}
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Time</div>
                  <div className="font-mono font-medium text-sm">
                    <AnimatedNumber 
                      value={totalTime / 1000} 
                      isStreaming={isStreaming}
                      suffix="s"
                      decimals={1}
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Tools</div>
                  <div className="font-mono font-medium text-sm">
                    {stats.totalTools}
                  </div>
                </div>
              </div>
            </div>
            
            {stats.totalTools > 0 && (stats.successfulTools > 0 || stats.failedTools > 0) && (
              <div className="mt-3 pt-2 border-t border-border/50">
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-green-600">
                    {stats.successfulTools} success
                  </span>
                  <span className="text-destructive">
                    {stats.failedTools} failed
                  </span>
                </div>
              </div>
            )}
          </motion.div>
          
          {!hasActivity && (
            <div className="text-center py-8 px-4">
              <Brain className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">
                No activity yet. Send a message to start.
              </p>
            </div>
          )}
          
          {thoughts.length > 0 && (
            <div>
              <button
                onClick={() => setShowThoughts(!showThoughts)}
                className="w-full flex items-center justify-between px-2 py-1.5 text-sm font-medium hover:bg-muted/50 rounded-sm transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-muted-foreground" />
                  Thoughts
                  <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded-sm">
                    {thoughts.length}
                  </span>
                </div>
                {showThoughts ? (
                  <ChevronUp className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                )}
              </button>
              
              <AnimatePresence>
                {showThoughts && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="mt-2 space-y-2"
                  >
                    {thoughts.map((thought, idx) => (
                      <div
                        key={idx}
                        className="bg-muted/30 rounded-sm p-2.5 text-xs text-muted-foreground border border-border/30"
                      >
                        <div className="flex items-start gap-2">
                          <Brain className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <div className="whitespace-pre-wrap">{thought.content}</div>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
          
          {toolCalls.length > 0 && (
            <div>
              <button
                onClick={() => setShowTools(!showTools)}
                className="w-full flex items-center justify-between px-2 py-1.5 text-sm font-medium hover:bg-muted/50 rounded-sm transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-muted-foreground" />
                  Tool Calls
                  <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded-sm">
                    {toolCalls.length}
                  </span>
                </div>
                {showTools ? (
                  <ChevronUp className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                )}
              </button>
              
              <AnimatePresence>
                {showTools && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="mt-2 space-y-2"
                  >
                    {toolCalls.map((call, idx) => (
                      <ToolCallDisplay key={idx} toolCall={call} />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export type { AgentActivityPanelProps as AgentActivityPanelPropsType };