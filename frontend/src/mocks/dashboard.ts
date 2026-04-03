// TODO: Replace with API call in future phase
// Mock data for Dashboard page

export interface ChartDataPoint {
  name: string;
  uv: number;
}

export interface PieChartDataPoint {
  name: string;
  value: number;
}

export interface KPIStats {
  totalPapers: { value: number; unit: string };
  entitiesExtracted: { value: number; unit: string };
  knowledgeGraph: { value: number; unit: string };
  llmGenerations: { value: number; unit: string };
  tokensProcessed: { value: number; unit: string };
  deepReads: { value: number; unit: string };
  analyzedDocs: { value: number; unit: string };
  globalQueries: { value: number; unit: string };
  externalSearches: { value: number; unit: string };
}

// AreaChart data (monthly trend)
export const AREA_CHART_DATA_ZH: ChartDataPoint[] = [
  { name: '一月', uv: 4000 },
  { name: '二月', uv: 3000 },
  { name: '三月', uv: 2000 },
  { name: '四月', uv: 2780 },
  { name: '五月', uv: 1890 },
  { name: '六月', uv: 2390 },
  { name: '七月', uv: 3490 },
];

export const AREA_CHART_DATA_EN: ChartDataPoint[] = [
  { name: 'Jan', uv: 4000 },
  { name: 'Feb', uv: 3000 },
  { name: 'Mar', uv: 2000 },
  { name: 'Apr', uv: 2780 },
  { name: 'May', uv: 1890 },
  { name: 'Jun', uv: 2390 },
  { name: 'Jul', uv: 3490 },
];

// PieChart data (subject distribution)
export const PIE_CHART_DATA_ZH: PieChartDataPoint[] = [
  { name: '图数据库', value: 400 },
  { name: 'LLM 智能体', value: 300 },
  { name: 'RAG 模型', value: 300 },
  { name: '视觉 AI', value: 200 },
];

export const PIE_CHART_DATA_EN: PieChartDataPoint[] = [
  { name: 'Graph DB', value: 400 },
  { name: 'LLM Agents', value: 300 },
  { name: 'RAG Models', value: 300 },
  { name: 'Vision AI', value: 200 },
];

// Pie chart colors
export const PIE_COLORS = ['#d35400', '#e67e22', '#2d241e', '#7a6b5d'];

// KPI statistics
export const KPI_STATS_ZH: KPIStats = {
  totalPapers: { value: 2847, unit: '篇' },
  entitiesExtracted: { value: 15429, unit: '个' },
  knowledgeGraph: { value: 847, unit: '节点' },
  llmGenerations: { value: 329, unit: '次' },
  tokensProcessed: { value: 1.2, unit: 'M' },
  deepReads: { value: 156, unit: '篇' },
  analyzedDocs: { value: 892, unit: '份' },
  globalQueries: { value: 429, unit: '次' },
  externalSearches: { value: 67, unit: '次' },
};

export const KPI_STATS_EN: KPIStats = {
  totalPapers: { value: 2847, unit: 'papers' },
  entitiesExtracted: { value: 15429, unit: 'entities' },
  knowledgeGraph: { value: 847, unit: 'nodes' },
  llmGenerations: { value: 329, unit: 'runs' },
  tokensProcessed: { value: 1.2, unit: 'M' },
  deepReads: { value: 156, unit: 'papers' },
  analyzedDocs: { value: 892, unit: 'docs' },
  globalQueries: { value: 429, unit: 'queries' },
  externalSearches: { value: 67, unit: 'searches' },
};

// Helper functions to get data based on language
export function getAreaChartData(isZh: boolean): ChartDataPoint[] {
  return isZh ? AREA_CHART_DATA_ZH : AREA_CHART_DATA_EN;
}

export function getPieChartData(isZh: boolean): PieChartDataPoint[] {
  return isZh ? PIE_CHART_DATA_ZH : PIE_CHART_DATA_EN;
}

export function getKPIStats(isZh: boolean): KPIStats {
  return isZh ? KPI_STATS_ZH : KPI_STATS_EN;
}