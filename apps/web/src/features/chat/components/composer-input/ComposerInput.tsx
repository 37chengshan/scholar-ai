import { ChevronDown, Loader2, Send, Square, Paperclip } from 'lucide-react';
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
    <div className="px-4 pb-4 pt-2 bg-gradient-to-t from-background via-background to-transparent">
      <div className="max-w-3xl mx-auto">
        {/* Floating input container */}
        <div className="bg-white rounded-2xl shadow-lg ring-1 ring-black/[0.06] focus-within:ring-primary/30 focus-within:shadow-xl transition-all">
          {/* Textarea area */}
          <div className="flex items-end gap-2 px-4 pt-3 pb-2">
            <textarea
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="flex-1 text-sm bg-transparent resize-none outline-none min-h-[44px] max-h-[180px] leading-relaxed placeholder:text-zinc-400"
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
                  disabled={disabled && !streaming}
                  className="flex items-center gap-1 text-[11px] font-medium text-zinc-500 hover:text-zinc-800 transition-colors px-2 py-1 rounded-lg hover:bg-zinc-100"
                >
                  <span className={clsx(
                    'w-1.5 h-1.5 rounded-full',
                    mode === 'auto' ? 'bg-primary/70' : mode === 'rag' ? 'bg-emerald-500' : 'bg-violet-500'
                  )} />
                  {currentMode.label}
                  <ChevronDown className="w-3 h-3" />
                </button>
                {modeMenuOpen && (
                  <div className="absolute bottom-full mb-1 left-0 bg-white border border-zinc-200 rounded-xl shadow-lg z-50 min-w-[180px] overflow-hidden py-1">
                    {modeOptions.map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => handleModeSelect(opt.value)}
                        className={clsx(
                          'w-full text-left px-3 py-2 text-xs transition-colors flex items-center gap-2',
                          mode === opt.value
                            ? 'bg-primary/8 text-primary font-semibold'
                            : 'hover:bg-zinc-50 text-zinc-700'
                        )}
                      >
                        <span className={clsx(
                          'w-1.5 h-1.5 rounded-full flex-shrink-0',
                          opt.value === 'auto' ? 'bg-primary/70' : opt.value === 'rag' ? 'bg-emerald-500' : 'bg-violet-500'
                        )} />
                        <span>{opt.label}</span>
                        <span className="text-[10px] text-zinc-400 ml-auto">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: send/stop button */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-400 font-mono hidden sm:inline">{labels.sendKeyHint}</span>
              {streaming && onStop ? (
                <button
                  onClick={onStop}
                  className="w-8 h-8 flex items-center justify-center bg-zinc-800 text-white rounded-full hover:bg-zinc-600 transition-colors flex-shrink-0"
                  title={isZh ? '停止生成' : 'Stop generation'}
                >
                  <Square className="w-3 h-3" />
                </button>
              ) : (
                <button
                  onClick={onSend}
                  disabled={!input.trim() || disabled}
                  className={clsx(
                    'w-8 h-8 flex items-center justify-center rounded-full transition-all flex-shrink-0',
                    input.trim() && !disabled
                      ? 'bg-primary text-white hover:bg-primary/90 shadow-sm'
                      : 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
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

