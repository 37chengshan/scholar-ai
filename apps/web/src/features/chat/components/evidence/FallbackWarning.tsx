interface FallbackWarningProps {
  visible: boolean;
  reason?: string | null;
}

export function FallbackWarning({ visible, reason }: FallbackWarningProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="mt-2 rounded-md border border-amber-500/45 bg-amber-500/12 px-2.5 py-2 text-[11px] text-amber-800">
      fallback active{reason ? ` (${reason})` : ''}
    </div>
  );
}
