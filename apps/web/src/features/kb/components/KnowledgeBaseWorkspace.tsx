import { KnowledgeBaseDetailLegacy } from './KnowledgeBaseDetailLegacy';
import { useSearchParams } from 'react-router';

export function KnowledgeBaseWorkspace() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') ?? 'papers';

  return (
    <section data-testid="kb-workspace-root" data-active-tab={activeTab}>
      <KnowledgeBaseDetailLegacy />
    </section>
  );
}
