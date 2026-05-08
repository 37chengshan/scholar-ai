export function isSafeNavigationTarget(target: string): boolean {
  return target.startsWith('/') || target.startsWith('http://') || target.startsWith('https://');
}

export function openSafeExternalLink(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

export function navigateToSafeTarget(
  target: string | null | undefined,
  navigate: (to: string) => void,
): boolean {
  if (!target || !isSafeNavigationTarget(target)) {
    return false;
  }

  if (target.startsWith('/')) {
    navigate(target);
    return true;
  }

  openSafeExternalLink(target);
  return true;
}