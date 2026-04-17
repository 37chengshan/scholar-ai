import { useSearchParams } from 'react-router';
import { KnowledgeWorkspaceShell } from './KnowledgeWorkspaceShell';

export function KnowledgeBaseWorkspace() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') ?? 'papers';

  return (
    <section data-testid="kb-workspace-root" data-active-tab={activeTab}>
      <KnowledgeWorkspaceShell />
    </section>
  );
}
