import { ChevronDown, Loader2, Send, Square } from 'lucide-react';
import { clsx } from 'clsx';
import { useState, useRef } from 'react';

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
  streaming?: boolean; // true when SSE stream is active
  placeholder: string;
  labels: ComposerInputCopy;
  onModeChange: (mode: 'auto' | 'rag' | 'agent') => void;
  onInputChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  onStop?: () => void;
}

const MODE_OPTIONS_ZH = [
  { value: 'auto' as const, label: '自动', desc: '系统自动选择' },
  { value: 'rag' as const, label: '快速问答', desc: '直接检索回答' },
  { value: 'agent' as const, label: '深度分析', desc: '多步 Agent 推理' },
];
const MODE_OPTIONS_EN = [
  { value: 'auto' as const, label: 'Auto', desc: 'Automatic routing' },
  { value: 'rag' as const, label: 'Fast RAG', desc: 'Direct retrieval' },
  { value: 'agent' as const, label: 'Deep Agent', desc: 'Multi-step reasoning' },
];

export function ComposerInput({
  scopeType,
  isZh,
  mode,
  input,
  disabled,
  streaming = false,
  placeholder,
  labels,
  onModeChange,
  onInputChange,
  onKeyDown,
  onSend,
  onStop,
}: ComposerInputProps) {
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const modeOptions = isZh ? MODE_OPTIONS_ZH : MODE_OPTIONS_EN;
  const currentMode = modeOptions.find(o => o.value === mode) ?? modeOptions[0];
  const menuRef = useRef<HTMLDivElement>(null);

  const handleModeSelect = (val: 'auto' | 'rag' | 'agent') => {
    onModeChange(val);
    setModeMenuOpen(false);
  };

  return (
    <div className="border-t border-border/50 bg-background/85 px-4 pb-4 pt-2 backdrop-blur-md">
      <div className="mx-auto max-w-full" style={{ width: 'min(100%, var(--composer-max-width))' }}>
        <div
          data-testid="chat-composer"
          className={clsx(
            'rounded-2xl border border-border/70 bg-card shadow-sm transition-all',
            'focus-within:border-primary/35 focus-within:ring-2 focus-within:ring-primary/10',
            disabled && !streaming && 'opacity-70',
          )}
        >
          {/* Textarea area */}
          <div className="flex items-end gap-2 px-4 pt-3 pb-2">
            <textarea
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="min-h-[2.75rem] max-h-[11.25rem] flex-1 resize-none bg-transparent text-[var(--font-sm)] leading-relaxed outline-none placeholder:text-muted-foreground"
              rows={1}
              disabled={disabled && !streaming}
              onInput={(event) => {
                const target = event.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = `${Math.min(target.scrollHeight, 180)}px`;
              }}
            />
          </div>

          {/* Bottom bar: mode + actions */}
          <div className="flex items-center justify-between px-3 pb-2.5">
            {/* Left: mode selector */}
            <div className="flex items-center gap-1">
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setModeMenuOpen(v => !v)}
                  disabled={streaming || (disabled && !streaming)}
                  title={streaming ? (isZh ? '生成中不可切换模式' : 'Mode cannot change while streaming') : undefined}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <span className={clsx(
                    'w-1.5 h-1.5 rounded-full',
                    mode === 'auto' ? 'bg-primary/70' : mode === 'rag' ? 'bg-secondary' : 'bg-muted-foreground'
                  )} />
                  {currentMode.label}
                  <ChevronDown className="w-3 h-3" />
                </button>
                {modeMenuOpen && (
                  <div className="absolute bottom-full left-0 z-50 mb-1 min-w-[180px] overflow-hidden rounded-xl border border-border bg-card py-1 shadow-md">
                    {modeOptions.map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => handleModeSelect(opt.value)}
                        disabled={streaming}
                        className={clsx(
                          'w-full text-left px-3 py-2 text-xs transition-colors flex items-center gap-2',
                          mode === opt.value
                            ? 'bg-primary/8 text-primary font-semibold'
                            : 'hover:bg-muted text-foreground/80',
                          streaming && 'opacity-60 cursor-not-allowed'
                        )}
                      >
                        <span className={clsx(
                          'w-1.5 h-1.5 rounded-full flex-shrink-0',
                          opt.value === 'auto' ? 'bg-primary/70' : opt.value === 'rag' ? 'bg-secondary' : 'bg-muted-foreground'
                        )} />
                        <span>{opt.label}</span>
                        <span className="text-[10px] text-muted-foreground ml-auto hidden md:inline">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: send/stop button */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground hidden sm:inline">{labels.sendKeyHint}</span>
              {streaming && onStop ? (
                <button
                  onClick={onStop}
                  className="w-8 h-8 flex items-center justify-center bg-foreground text-background rounded-full hover:bg-foreground/80 transition-colors flex-shrink-0"
                  title={isZh ? '停止生成' : 'Stop generation'}
                >
                  <Square className="w-3 h-3" />
                </button>
              ) : (
                <button
                  onClick={onSend}
                  disabled={!input.trim() || disabled}
                  title={!input.trim() ? (isZh ? '请输入问题' : 'Type a message first') : disabled ? (isZh ? '当前不可发送' : 'Cannot send right now') : undefined}
                  aria-label={isZh ? '发送消息' : 'Send message'}
                  className={clsx(
                    'w-8 h-8 flex items-center justify-center rounded-full transition-all flex-shrink-0',
                    input.trim() && !disabled
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm'
                      : 'bg-muted text-muted-foreground cursor-not-allowed'
                  )}
                >
                  {disabled ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

