import { AlertCircle, Loader2, Send } from 'lucide-react';
import { clsx } from 'clsx';

interface ComposerInputCopy {
  mode: string;
  verify: string;
  sendKeyHint: string;
}

interface ComposerInputProps {
  scopeType: string | null;
  isZh: boolean;
  mode: 'auto' | 'rag' | 'agent';
  input: string;
  disabled: boolean;
  placeholder: string;
  labels: ComposerInputCopy;
  onModeChange: (mode: 'auto' | 'rag' | 'agent') => void;
  onInputChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
}

export function ComposerInput({
  scopeType,
  isZh,
  mode,
  input,
  disabled,
  placeholder,
  labels,
  onModeChange,
  onInputChange,
  onKeyDown,
  onSend,
}: ComposerInputProps) {
  return (
    <div className="px-6 py-4 border-t border-zinc-200 bg-background">
      <div className="max-w-4xl mx-auto">
        {scopeType !== null && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-muted-foreground">{labels.mode}:</span>
            <div className="flex rounded-lg border border-border overflow-hidden text-xs">
              {[
                { value: 'auto' as const, label: isZh ? '自动' : 'Auto' },
                { value: 'rag' as const, label: isZh ? '快速问答' : 'Fast RAG' },
                { value: 'agent' as const, label: isZh ? '深度分析' : 'Deep Agent' },
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => onModeChange(option.value)}
                  disabled={disabled}
                  className={clsx(
                    'px-3 py-1 transition-colors',
                    mode === option.value
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card hover:bg-muted text-muted-foreground'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex items-end gap-3 bg-transparent rounded-none border-b border-zinc-300 focus-within:border-primary transition-colors pb-2">
          <textarea
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            className="flex-1 p-1 text-[15px] font-serif bg-transparent resize-none outline-none min-h-[40px] max-h-[160px] placeholder:font-sans placeholder:text-[12px] placeholder:uppercase placeholder:tracking-widest"
            rows={1}
            disabled={disabled}
            onInput={(event) => {
              const target = event.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
            }}
          />
          <button
            onClick={onSend}
            disabled={!input.trim() || disabled}
            className={clsx(
              'w-9 h-9 border border-zinc-300 flex items-center justify-center transition-all disabled:opacity-30',
              input.trim() && !disabled
                ? 'bg-zinc-900 text-white hover:bg-primary hover:border-primary'
                : 'bg-zinc-100 text-zinc-500'
            )}
          >
            {disabled ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 -ml-0.5" />}
          </button>
        </div>
        <div className="flex justify-between items-center mt-4 px-1 font-mono text-[9px] uppercase tracking-widest text-ink/40">
          <span className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> {labels.verify}
          </span>
          <span>{labels.sendKeyHint}</span>
        </div>
      </div>
    </div>
  );
}
