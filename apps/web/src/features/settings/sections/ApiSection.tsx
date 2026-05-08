import { APIKeyManager } from '@/app/components/APIKeyManager';

interface ApiSectionProps {
  isZh: boolean;
}

export function ApiSection({ isZh }: ApiSectionProps) {
  return <APIKeyManager isZh={isZh} />;
}
