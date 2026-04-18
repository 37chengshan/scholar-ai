import { useSearchParams } from 'react-router';
import { KnowledgeBaseDetailV2 } from './KnowledgeBaseDetailV2';

export function KnowledgeBaseWorkspace() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') ?? 'papers';

  return (
    <section data-testid="kb-workspace-root" data-active-tab={activeTab}>
      <KnowledgeBaseDetailV2 />
    </section>
  );
}
