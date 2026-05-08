import type { KnowledgeBase } from '@/services/kbApi';

type KnowledgeBaseDisplaySource = Pick<KnowledgeBase, 'id' | 'name' | 'description'>;

export interface KnowledgeBaseDisplayMetadata {
  displayName: string;
  displayDescription: string;
  isFixtureNormalized: boolean;
}

const FIXTURE_NAME_PATTERNS = [
  /^phase2-online-verify-/i,
  /^phase2-beta-/i,
  /^phased-rwt/i,
  /^e2e-kb-/i,
  /^scholarai-beta-/i,
];

const FIXTURE_DESCRIPTION_PATTERNS = [
  /phase2 online provider verification/i,
  /critical e2e knowledge base creation/i,
  /controlled beta/i,
  /real validation chain/i,
  /reset proof naming contract/i,
];

function isFixtureLabel(name: string, description: string): boolean {
  return FIXTURE_NAME_PATTERNS.some((pattern) => pattern.test(name))
    || FIXTURE_DESCRIPTION_PATTERNS.some((pattern) => pattern.test(description));
}

function extractDisplayToken(source: KnowledgeBaseDisplaySource): string {
  const fromName = source.name.match(/([a-z0-9]{4})$/i)?.[1];
  if (fromName) {
    return fromName.toUpperCase();
  }

  const compactId = source.id.replace(/-/g, '');
  return compactId.slice(-4).toUpperCase();
}

function buildFixtureDisplayName(source: KnowledgeBaseDisplaySource): string {
  const token = extractDisplayToken(source);

  if (/phased-rwt/i.test(source.name)) {
    return `研究问题资料馆 ${token}`;
  }

  if (/e2e-kb/i.test(source.name)) {
    return `学术资料馆 ${token}`;
  }

  if (/scholarai-beta-/i.test(source.name)) {
    return `文献工作区 ${token}`;
  }

  return `研究资料馆 ${token}`;
}

function buildFixtureDescription(source: KnowledgeBaseDisplaySource): string {
  if (/phased-rwt/i.test(source.name) || /real validation chain/i.test(source.description)) {
    return '围绕研究问题沉淀论文、证据与分析结论的工作区。';
  }

  if (/e2e-kb/i.test(source.name) || /critical e2e knowledge base creation/i.test(source.description)) {
    return '用于收纳核心论文并串联阅读、问答和笔记流程的资料馆。';
  }

  if (/scholarai-beta-/i.test(source.name) || /controlled beta|reset proof naming contract/i.test(source.description)) {
    return '围绕重点论文组织阅读、检索、问答与综述草稿的工作区。';
  }

  return '围绕已导入论文建立检索、阅读、问答与笔记的研究工作区。';
}

export function getKnowledgeBaseDisplayMetadata(source: KnowledgeBaseDisplaySource): KnowledgeBaseDisplayMetadata {
  if (!isFixtureLabel(source.name, source.description)) {
    return {
      displayName: source.name,
      displayDescription: source.description,
      isFixtureNormalized: false,
    };
  }

  return {
    displayName: buildFixtureDisplayName(source),
    displayDescription: buildFixtureDescription(source),
    isFixtureNormalized: true,
  };
}
