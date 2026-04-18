import { KnowledgeBaseDetailV2 } from '@/features/kb/components/KnowledgeBaseDetailV2';

// LEGACY BRIDGE (Plan A W4):
// - KnowledgeBaseDetailLegacy main body has been replaced by V2 shell + feature hooks.
// - Keep this file as a compatibility bridge during one release window.
export function KnowledgeBaseDetailLegacy() {
  return <KnowledgeBaseDetailV2 />;
}
