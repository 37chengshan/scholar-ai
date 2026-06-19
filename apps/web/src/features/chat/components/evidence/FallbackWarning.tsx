interface FallbackWarningProps {
  visible: boolean;
  reason?: string | null;
}

export function FallbackWarning({ visible, reason }: FallbackWarningProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="mt-2 rounded-md border border-[var(--color-warning)]/45 bg-[var(--color-warning)]/12 px-2.5 py-2 text-[11px] text-[var(--color-warning)]">
      fallback active{reason ? ` (${reason})` : ''}
    </div>
  );
}
