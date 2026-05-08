export const ACTIVE_GENERATION_MODEL = 'glm-4.6v-flashx';
export const ACTIVE_EMBEDDING_MODEL = 'text-embedding-v4';
export const ACTIVE_RERANK_MODEL = 'qwen3-rerank';

const EMBEDDING_MODEL_LABELS: Record<string, string> = {
  'qwen_flash': 'DashScope text-embedding-v4',
  'qwen_pro': 'DashScope text-embedding-v4',
  'text-embedding-v4': 'DashScope text-embedding-v4',
  'bge-m3': 'BGE-M3',
};

const GENERATION_MODEL_LABELS: Record<string, string> = {
  'glm-4.6v-flashx': '智谱 GLM-4.6V-FlashX',
  'glm-4-flash': '智谱 GLM-4-Flash',
};

const PARSE_ENGINE_LABELS: Record<string, string> = {
  'docling': 'Docling 解析',
};

export function formatEmbeddingModelLabel(model: string | null | undefined): string {
  const normalized = (model || '').trim();
  if (!normalized) {
    return 'Unknown Embedding';
  }
  return EMBEDDING_MODEL_LABELS[normalized] || normalized;
}

export function formatGenerationModelLabel(model: string | null | undefined): string {
  const normalized = (model || '').trim();
  if (!normalized) {
    return 'Unknown Model';
  }
  return GENERATION_MODEL_LABELS[normalized] || normalized;
}

export function formatParseEngineLabel(engine: string | null | undefined): string {
  const normalized = (engine || '').trim().toLowerCase();
  if (!normalized) {
    return '未知解析流程';
  }
  return PARSE_ENGINE_LABELS[normalized] || engine || '未知解析流程';
}
