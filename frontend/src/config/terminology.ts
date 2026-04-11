/**
 * ScholarAI 前端术语规范表
 * 
 * 使用规则：
 * 1. 面向用户的功能名称使用中文术语
 * 2. 技术细节可用工程术语，但需用中文解释
 * 3. 外部服务名称保持英文（如 Semantic Scholar）
 * 4. API 路径保持英文（不影响用户 UI）
 */

// 用户面术语（中文）
export const TERMINOLOGY_USER: Record<string, string> = {
  // 核心功能
  'paper': '论文',
  'papers': '论文库',
  'knowledge-base': '知识库',
  'knowledge-bases': '知识库列表',
  'kb-retrieval': '知识库检索',
  'kb-qa': '问答',
  
  // 操作动作
  'upload': '上传',
  'search': '搜索',
  'read': '阅读',
  'chat': '对话',
  'notes': '笔记',
  'annotations': '批注',
  'session': '对话',
  'sessions': '对话历史',
  'query': '问答',
  'query-result': '问答结果',
  
  // 文档结构
  'citation': '引用',
  'citations': '引用来源',
  'snippet': '片段',
  'abstract': '摘要',
  'authors': '作者',
  'keywords': '关键词',
  'tags': '标签',
  
  // 进度与状态
  'progress': '阅读进度',
  'import': '导入',
  'export': '导出',
  'batch-delete': '批量删除',
  'batch-export': '批量导出',
  'storage': '存储空间',
  'dashboard': '仪表盘',
  'settings': '设置',
  'profile': '个人资料',
  
  // 动作术语
  'create': '创建',
  'edit': '编辑',
  'delete': '删除',
  'save': '保存',
  'cancel': '取消',
  'confirm': '确认',
  'refresh': '刷新',
  'retry': '重试',
  'view': '查看',
  'read-paper': '阅读论文',
  'import-paper': '导入论文',
  'add-to-kb': '添加到知识库',
  'send-query': '发送问答',
  
  // 状态术语
  'loading': '加载中',
  'processing': '处理中',
  'indexing': '建立索引中',
  'uploading': '上传中',
  'querying': '查询中',
  'saving': '保存中',
  'success': '成功',
  'error': '失败',
  'warning': '警告',
  'empty': '暂无内容',
  'ready': '就绪',
  'active': '活跃',
  'inactive': '未激活',
  'synced': '已同步',
  'outdated': '待更新',
  
  // 时间术语
  'last-update': '上次更新',
  'created-at': '创建时间',
  'updated-at': '更新时间',
  'last-read': '上次阅读',
  'minutes-ago': '分钟前',
  'hours-ago': '小时前',
  'days-ago': '天前',
  
  // 删除确认
  'delete-confirm': '确定要删除吗？',
  'delete-confirm-session': '确定要删除这个对话吗？删除后将无法恢复。',
  'logout-confirm': '确定要退出登录吗？退出后需要重新登录才能使用。',
};

// 内部工程术语（不在用户 UI 直接展示）
export const TERMINOLOGY_INTERNAL: Record<string, string> = {
  'vector-search': '向量检索',
  'embedding': '文本嵌入',
  'rag': 'RAG',
  'llm': 'LLM',
  'semantic-scholar': 'Semantic Scholar API',
  'pdf-parse': 'PDF 解析',
  'chunk': '文本块',
  'node': '节点',
  'api-status': 'API 状态',
  'db-status': '数据库状态',
};

// 术语使用规则
export const TERMINOLOGY_RULES = {
  // 规则 1：面向用户的功能名称使用中文
  userFacingTerms: true,
  
  // 规则 2：技术细节和内部状态使用工程术语，但用中文解释
  internalTermsWithExplanation: true,
  
  // 规则 3：外部服务名称保持英文（如 Semantic Scholar）
  externalServiceNames: true,
  
  // 规则 4：API 路径保持英文（不影响用户 UI）
  apiPaths: false, // 不在 UI 展示
};

/**
 * 获取用户界面术语
 * @param key - 术语键
 * @returns 中文术语
 */
export const getTerm = (key: string): string => {
  return TERMINOLOGY_USER[key] || key;
};

/**
 * 获取内部工程术语（带中文解释）
 * @param key - 工程术语键
 * @returns 中文解释
 */
export const getInternalTerm = (key: string): string => {
  return TERMINOLOGY_INTERNAL[key] || key;
};

/**
 * 检查是否是用户界面术语
 * @param key - 术语键
 * @returns 是否是用户界面术语
 */
export const isUserTerm = (key: string): boolean => {
  return key in TERMINOLOGY_USER;
};