/**
 * TerminalOutputCard Component
 *
 * Displays execute_command tool result in terminal-style dark box.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Terminal, AlertCircle } from 'lucide-react';

interface TerminalOutputCardProps {
  result: {
    command: string;
    output: string;
    exit_code?: number;
  };
}

export function TerminalOutputCard({ result }: TerminalOutputCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const exitCode = result.exit_code ?? 0;
  const hasError = exitCode !== 0;

  return (
    <div className="rounded-lg overflow-hidden border border-border/50">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 text-gray-300">
        <Terminal className="w-4 h-4" />
        <span className="text-xs font-mono">{isZh ? '命令执行' : 'Command'}</span>
      </div>

      {/* Terminal body */}
      <div className="bg-gray-900 text-green-400 font-mono text-xs rounded-b-lg p-4">
        {/* Command line */}
        <div className="text-white mb-2">
          <span className="text-gray-500">$ </span>
          {result.command}
        </div>

        {/* Output */}
        {result.output && (
          <pre className="whitespace-pre-wrap break-words max-h-48 overflow-y-auto text-green-400">
            {result.output}
          </pre>
        )}

        {/* Exit code */}
        {hasError && (
          <div className="flex items-center gap-1.5 text-red-400 mt-2 pt-2 border-t border-gray-700">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>
              {isZh ? `退出码` : `Exit code`}: {exitCode}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
