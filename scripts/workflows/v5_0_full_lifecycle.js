export const meta = {
  name: 'v5-0-full-lifecycle',
  description: 'ScholarAI v5.0 完整生命周期：分支创建 → 10 phase 循环(研究→审查→计划→执行→测试→文档) → PR → CI 监控 → 合并',
  phases: [
    { title: 'Branch Setup', detail: '创建 feat/v5-0 分支' },
    { title: 'Phase 5.0-0', detail: 'Foundation + v4.x Migration + Audit Baseline' },
    { title: 'Phase 5.0-1', detail: 'Design System v2 + Magazine Editorial' },
    { title: 'Phase 5.0-2', detail: 'WorkspaceShell v2 + Performance' },
    { title: 'Phase 5.0-3', detail: 'Upload Visualization Full Chain' },
    { title: 'Phase 5.0-4', detail: 'Read Page + Pretext Engine' },
    { title: 'Phase 5.0-5', detail: 'Notes Deep Refactoring' },
    { title: 'Phase 5.0-6', detail: 'Chat Polish + Chat-Notes Bridge' },
    { title: 'Phase 5.0-7', detail: 'Backend Pipeline Stability' },
    { title: 'Phase 5.0-8', detail: 'RAG SOTA Deep Expansion' },
    { title: 'Phase 5.0-9', detail: 'Full-chain Walkthrough + Release Gate' },
    { title: 'PR & Merge', detail: '创建 PR → 监视 CI → 合并' },
  ],
}

// ══════════════════════════════════════════════════════════
// 配置
// ══════════════════════════════════════════════════════════

// 🔒 视觉任务模型限制
// 所有视觉理解、图片截图理解、浏览器审查任务必须使用 mimov2.5
// 禁止使用 v2.5pro 进行图片理解
const VISUAL_MODEL = 'mimov2.5'  // 截图理解、Playwright 审查、Lighthouse 视觉分析
const CODE_MODEL = 'sonnet'      // 代码生成、审查、执行
const LIGHT_MODEL = 'haiku'      // 简单任务、文档更新、提交

// 安全获取 args（workflow 运行时注入的全局变量）
// 注意：args 是 Workflow 工具注入的全局变量，如果未传入则为 undefined
let SKIP_PHASES = []
try {
  // 调试：输出 args 的类型和值
  log(`[DEBUG] args type: ${typeof args}, value: ${JSON.stringify(args)}`)
  if (typeof args !== 'undefined' && args && args.skipPhases) {
    SKIP_PHASES = args.skipPhases
    log(`[DEBUG] SKIP_PHASES from args: ${JSON.stringify(SKIP_PHASES)}`)
  } else {
    log(`[DEBUG] args.skipPhases not found, using empty array`)
  }
} catch (e) {
  log(`[DEBUG] args error: ${e.message}`)
}
// 也支持从环境变量读取（备用方案）
if (SKIP_PHASES.length === 0 && typeof process !== 'undefined' && process.env?.SKIP_PHASES) {
  try {
    SKIP_PHASES = JSON.parse(process.env.SKIP_PHASES)
    log(`[DEBUG] SKIP_PHASES from env: ${JSON.stringify(SKIP_PHASES)}`)
  } catch (e) {
    SKIP_PHASES = process.env.SKIP_PHASES.split(',')
    log(`[DEBUG] SKIP_PHASES from env (split): ${JSON.stringify(SKIP_PHASES)}`)
  }
}
log(`[DEBUG] Final SKIP_PHASES: ${JSON.stringify(SKIP_PHASES)}`)

// 文档路径
const DOCS = {
  planStatus: 'docs/plans/PLAN_STATUS.md',
  ledger: 'docs/specs/governance/phase-delivery-ledger.md',
  v5Readme: 'docs/plans/v5_0/README.md',
  checkpoint: 'docs/plans/v5_0/.workflow_checkpoint.json',
}

// Phase 定义（所有工作在 feat/v5-0 分支上完成）
const PHASES = [
  { id: '5.0-0', name: 'Foundation', slug: 'foundation', wave: 0,
    goal: '治理切换 + v4.x 迁移 + Audit Baseline，不动业务代码',
    scope: 'v4.x migration inventory, runtime contract freeze, gate input matrix, perf baseline, audit baseline',
    files: ['docs/plans/v5_0/', 'scripts/evals/run_v5_release_gate.py', 'docs/plans/PLAN_STATUS.md', 'docs/specs/governance/phase-delivery-ledger.md'],
    deps: [], layer: 'docs' },
  { id: '5.0-1', name: 'Design System v2', slug: 'design-system-v2', wave: 1,
    goal: 'CSS tokens 39→~200, oklch, dark theme, motion system, editorial typography, anti-template visual',
    scope: 'apps/web/src/styles/, apps/web/src/components/ui/, magazine.css inheritance, font stacks, color palette',
    files: ['apps/web/src/styles/', 'apps/web/src/components/ui/'],
    deps: ['5.0-0'], layer: 'frontend' },
  { id: '5.0-2', name: 'WorkspaceShell v2', slug: 'workspace-shell-v2', wave: 2,
    goal: '响应式 stack, Lighthouse CI, bundle budget ≤500KB, skeleton/loading/empty/error 四态',
    scope: 'apps/web/src/app/, vite.config.ts, lighthouse CI, bundle splitting, responsive layout',
    files: ['apps/web/src/app/', 'apps/web/vite.config.ts'],
    deps: ['5.0-0', '5.0-1'], layer: 'frontend' },
  { id: '5.0-3', name: 'Upload Visualization', slug: 'upload-visualization', wave: 3,
    goal: 'Upload.tsx 页面路由, 拖拽+队列, SSE 进度, mid-pipeline cancel, 批量上传聚合',
    scope: 'apps/web/src/app/pages/Upload.tsx, apps/web/src/features/uploads/, apps/api/app/api/imports/',
    files: ['apps/web/src/app/pages/Upload.tsx', 'apps/web/src/features/uploads/'],
    deps: ['5.0-1', '5.0-2'], layer: 'cross' },
  { id: '5.0-4', name: 'Read + Pretext', slug: 'read-pretext', wave: 4,
    goal: '@chenglou/pretext 引入, PDF annotation v2, linkedNote 双向同步, Read 页 0→6+ tests',
    scope: 'apps/web/src/features/read/, pretext adapter, PDF viewer, annotation system',
    files: ['apps/web/src/features/read/', 'apps/web/src/lib/pretext/'],
    deps: ['5.0-1', '5.0-2'], layer: 'frontend' },
  { id: '5.0-5', name: 'Notes Refactoring', slug: 'notes-refactoring', wave: 5,
    goal: 'TipTap 二次封装, block editing, @mention pills, pretext integration, artifact contract closeout',
    scope: 'apps/web/src/features/notes/, TipTap editor, notes↔paper/chunk/evidence links',
    files: ['apps/web/src/features/notes/'],
    deps: ['5.0-1', '5.0-2', '5.0-4'], layer: 'frontend' },
  { id: '5.0-6', name: 'Chat Polish', slug: 'chat-polish', wave: 6,
    goal: 'message virtualization, composer UX, citation panel, Chat↔Notes 双向桥, compare card UI',
    scope: 'apps/web/src/features/chat/, Chat↔Notes bridge, SSE/cancel/retry states',
    files: ['apps/web/src/features/chat/'],
    deps: ['5.0-1', '5.0-2', '5.0-4', '5.0-5'], layer: 'frontend' },
  { id: '5.0-7', name: 'Backend Pipeline', slug: 'backend-pipeline', wave: 1,
    goal: 'upload fail-closed, auth/ownership tests, trace_id 统一, observability SLO dashboard',
    scope: 'apps/api/app/api/, apps/api/app/services/, auth middleware, observability',
    files: ['apps/api/app/api/', 'apps/api/app/services/', 'apps/api/app/middleware/'],
    deps: ['5.0-0'], layer: 'backend' },
  { id: '5.0-8', name: 'RAG SOTA', slug: 'rag-sota', wave: 2,
    goal: 'RAPTOR-lite, review-only Graph synthesis, verifier fusion + NLI, comparative benchmark',
    scope: 'apps/api/app/rag_v3/, hierarchical_retriever, claim_verifier, graph synthesis',
    files: ['apps/api/app/rag_v3/', 'apps/api/app/services/'],
    deps: ['5.0-0', '5.0-7'], layer: 'backend' },
  { id: '5.0-9', name: 'Release Gate', slug: 'release-gate', wave: 9,
    goal: '7 E2E journeys, consolidated gate runner, multidimensional audit 二轮, 首份 release verdict',
    scope: 'scripts/evals/, e2e tests, governance scripts, release gate',
    files: ['scripts/evals/', 'apps/web/e2e/', 'docs/plans/v5_0/reports/'],
    deps: ['5.0-0', '5.0-1', '5.0-2', '5.0-3', '5.0-4', '5.0-5', '5.0-6', '5.0-7', '5.0-8'], layer: 'acceptance' },
]

// 审查维度
const REVIEW_DIMENSIONS = [
  { key: 'arch', label: '架构与可维护性',
    prompt: '审查架构分层、模块耦合、接口设计、依赖方向、代码边界合规性。' },
  { key: 'security', label: '安全与数据完整性',
    prompt: '审查 OWASP Top 10、输入验证、认证授权、密钥管理、数据泄露风险。' },
  { key: 'perf', label: '性能与可访问性',
    prompt: '审查 Core Web Vitals (LCP/INP/CLS)、bundle 体积、内存泄漏、N+1 查询、a11y 合规。' },
]

// ScholarAI 项目上下文（注入到每个 agent prompt）
const PROJECT_CONTEXT = `ScholarAI 是一个学术论文智能阅读系统。
技术栈：React 18 + TypeScript + Vite（前端）| Python FastAPI（后端）| PostgreSQL + PGVector + Neo4j + Redis
关键约束：apps/web 是前端唯一代码路径，apps/api 是后端唯一代码路径。
编码规范：不可变数据模式、函数 <50 行、文件 <800 行、TypeScript 严格类型。`

// ══════════════════════════════════════════════════════════
// 辅助函数
// ══════════════════════════════════════════════════════════

function phaseDir(slug) { return `docs/plans/v5_0/active/phase_${slug}` }
function reportDir() { return 'docs/plans/v5_0/reports' }
function today() { return new Date().toISOString().split('T')[0] }

/** 截断字符串，保留首尾（1M 上下文，40-59% 使用率 ≈ 400K-590K tokens） */
function truncate(str, maxLen = 30000) {
  if (!str) return '[empty]'
  if (str.length <= maxLen) return str
  const half = Math.floor(maxLen / 2)
  return str.substring(0, half) + `\n\n[... 中间省略 ${str.length - maxLen} 字符 ...]\n\n` + str.substring(str.length - half)
}

/** 检查是否为瞬态错误（可重试） */
function isTransientError(err) {
  const msg = (err.message || '').toLowerCase()
  return msg.includes('rate limit') || msg.includes('timeout')
    || msg.includes('503') || msg.includes('529')
    || msg.includes('overloaded') || msg.includes('econnreset')
}

/** 带重试的 agent 调用 */
async function agentWithRetry(prompt, opts = {}) {
  const { maxRetries = 2, baseDelay = 3000, label = '', ...agentOpts } = opts
  let lastError
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await agent(prompt, agentOpts)
    } catch (err) {
      lastError = err
      if (!isTransientError(err) || attempt === maxRetries) throw err
      const delay = baseDelay * Math.pow(2, attempt - 1)
      log(`⚠️ ${label} 失败 (${attempt}/${maxRetries}), ${delay}ms 后重试: ${err.message}`)
      await new Promise(r => setTimeout(r, delay))
    }
  }
  throw lastError
}

// ══════════════════════════════════════════════════════════
// STAGE 0: 分支创建
// ══════════════════════════════════════════════════════════
phase('Branch Setup')

log('🌿 创建 feat/v5-0 分支...')

await agentWithRetry(`
你是 Git 工作流专家。${PROJECT_CONTEXT}

请完成以下操作：
1. 确认当前分支状态和工作区是否干净
2. 如果有未提交的 v5.0 相关文件，先提交
3. 从 main 创建新分支 feat/v5-0（如果已存在则切换过去）
4. 推送到远程：git push -u origin feat/v5-0

执行完后报告：当前分支名、最新 commit hash、工作区状态。
`, { label: 'branch-setup', phase: 'Branch Setup', model: LIGHT_MODEL })

log('✅ 分支 feat/v5-0 就绪')

// ══════════════════════════════════════════════════════════
// STAGE 1: 逐 Phase 执行循环
// ══════════════════════════════════════════════════════════

for (const ph of PHASES) {
  // 跳过已完成的阶段
  if (SKIP_PHASES.includes(ph.id)) {
    log(`⏭️ 跳过 Phase ${ph.id}（已完成）`)
    continue
  }

  phase(`Phase ${ph.id}`)

  log(`\n${'═'.repeat(60)}`)
  log(`📦 Phase ${ph.id}: ${ph.name}`)
  log(`🎯 目标: ${ph.goal}`)
  log(`🔒 视觉模型: ${VISUAL_MODEL} | 代码模型: ${CODE_MODEL}`)
  log(`${'═'.repeat(60)}\n`)

  const pd = phaseDir(ph.slug)

  try {
    // ── Step 1: 研究 ─────────────────────────────────
    log(`📚 Step 1/8: 研究 Phase ${ph.id}...`)

    const research = await agentWithRetry(`
你是 ScholarAI 项目的技术研究员。${PROJECT_CONTEXT}

请对 Phase ${ph.id} 进行深度研究。

## Phase 信息
- **ID:** ${ph.id} | **名称:** ${ph.name}
- **目标:** ${ph.goal}
- **范围:** ${ph.scope}
- **涉及文件:** ${ph.files.join(', ')}
- **依赖:** ${ph.deps.length > 0 ? ph.deps.join(', ') : '无'}

## 研究要求
1. 读取涉及的文件/目录，理解现有实现状态
2. 确定技术方案、库、工具
3. 当前代码与目标之间的差距
4. 技术风险、依赖风险、范围风险
5. 按子任务拆分，估计复杂度

## 输出格式
输出结构化研究报告：现状分析、技术方案、子任务拆分、风险清单、依赖映射、工作量估计。
报告要具体、可操作、基于代码事实。
`, { label: `research:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    // 验证研究输出
    if (!research || research.length < 200) {
      throw new Error(`Phase ${ph.id} 研究输出不足 (${research?.length || 0} 字符)`)
    }

    // ── Step 2: 多维度审查研究 ────────────────────────
    log(`🔍 Step 2/8: 多维度审查研究...`)

    const researchReviews = await parallel(
      REVIEW_DIMENSIONS.map(d => () => agentWithRetry(`
你是 ScholarAI 项目的 ${d.label} 专家。${PROJECT_CONTEXT}

请审查 Phase ${ph.id} 研究报告（见下方）。

## 审查维度：${d.label}
${d.prompt}

## 研究报告（摘要）
${truncate(research, 20000)}

## 输出格式（严格遵守，每行一个字段）
VERDICT: [PASS | PASS-WITH-WARNINGS | FAIL]
CRITICAL_ISSUES: [逗号分隔，无则写 NONE]
HIGH_ISSUES: [逗号分隔，无则写 NONE]
IMPROVEMENTS: [逗号分隔，无则写 NONE]
`, { label: `review-research:${ph.id}:${d.key}`, phase: `Phase ${ph.id}`, model: CODE_MODEL }))
    )

    // 合成审查结果
    const researchReviewSynth = await agentWithRetry(`
综合以下三个维度的审查结果，给出 Phase ${ph.id} 研究报告的最终评价。

## 架构审查
${truncate(researchReviews[0], 8000)}

## 安全审查
${truncate(researchReviews[1], 8000)}

## 性能审查
${truncate(researchReviews[2], 8000)}

## 输出格式（严格遵守）
VERDICT: [PASS | PASS-WITH-WARNINGS | FAIL]
BLOCKING_ISSUES: [逗号分隔，无则写 NONE]
PROCEED_TO_PLANNING: [YES | NO]
PROCEED_CONDITIONS: [条件描述，无则写 NONE]
`, { label: `synth-research:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    // 验证门：检查是否可以进入计划阶段
    if (researchReviewSynth.includes('PROCEED_TO_PLANNING: NO')) {
      throw new Error(`Phase ${ph.id} 研究审查未通过，中止: ${researchReviewSynth.match(/PROCEED_CONDITIONS:(.*)/)?.[1] || '未知原因'}`)
    }

    // ── Step 3: 生成执行计划 ──────────────────────────
    log(`📋 Step 3/8: 生成执行计划...`)

    const plan = await agentWithRetry(`
你是 ScholarAI 项目的高级规划师。${PROJECT_CONTEXT}

请为 Phase ${ph.id} 生成执行计划。

## Phase 信息
- **ID:** ${ph.id} | **名称:** ${ph.name}
- **目标:** ${ph.goal}
- **范围:** ${ph.scope}
- **涉及文件:** ${ph.files.join(', ')}
- **层:** ${ph.layer}（frontend/backend/cross/docs）

## 研究报告（摘要）
${truncate(research, 15000)}

## 研究审查结论
${truncate(researchReviewSynth, 5000)}

## 计划格式
1. **Objective**: 清晰目标
2. **Tasks**: 每个 task 含 name / files / action / verify / done / type
3. **Wave 分组**: 按依赖关系分波
4. **Success Criteria**: 可衡量验收标准

每个 plan 最多 3 个 task，action 要具体可执行。
`, { label: `plan:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    // ── Step 4: 审查执行计划 ──────────────────────────
    log(`🔍 Step 4/8: 审查执行计划...`)

    const planReview = await agentWithRetry(`
你是项目计划审查专家。请审查 Phase ${ph.id} 执行计划。

## Phase 目标
${ph.goal}

## 执行计划（摘要）
${truncate(plan, 15000)}

## 审查维度
1. 完整性：是否覆盖 phase 目标？
2. 可行性：task action 是否具体可执行？
3. 依赖正确性：wave 分组是否合理？
4. 可验证性：verify 命令能否实际验证？
5. 范围控制：是否有范围蔓延？

## 输出格式（严格遵守）
VERDICT: [APPROVED | APPROVED-WITH-CHANGES | NEEDS-REVISION]
ISSUES: [逗号分隔，无则写 NONE]
CHANGES_REQUIRED: [逗号分隔，无则写 NONE]
PROCEED_TO_EXECUTION: [YES | NO]
`, { label: `review-plan:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    // 验证门：检查计划是否通过
    if (planReview.includes('PROCEED_TO_EXECUTION: NO')) {
      log(`⚠️ 计划需要修订，注入修订意见后继续执行...`)
    }

    // ── Step 5: 执行（启动子代理） ─────────────────────
    log(`⚡ Step 5/8: 执行 Phase ${ph.id}...`)

    let executionResult

    if (ph.layer === 'acceptance') {
      // Phase 5.0-9: 验收阶段
      executionResult = await agentWithRetry(`
你是 ScholarAI 的验收测试工程师。${PROJECT_CONTEXT}

请执行 Phase ${ph.id} 验收流程。

## 执行计划
${truncate(plan, 15000)}

## 验收任务
1. **E2E 测试**：运行 Playwright 测试（apps/web/e2e/）
2. **Release Gate**：python scripts/evals/run_v5_release_gate.py
3. **治理检查**：bash scripts/check-governance.sh
4. **Bundle 检查**：验证首屏 ≤ 500KB gzipped

报告每个任务 PASS/FAIL + 详情。
`, { label: `execute:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    } else if (ph.layer === 'backend') {
      // 后端 phase
      executionResult = await agentWithRetry(`
你是 ScholarAI 的 Python/FastAPI 后端工程师。${PROJECT_CONTEXT}

请执行 Phase ${ph.id}。

## 执行计划
${truncate(plan, 15000)}

## 重要约束
只执行与后端(apps/api/)相关的 task。跳过前端 task 并在报告中注明。

## 执行要求
1. 遵循 apps/api 的分层架构（api → services → repositories）
2. 使用 Pydantic 验证、structlog 日志
3. 为新功能编写 pytest 测试
4. 每个 task 完成后运行 verify 命令

报告每个 task 完成状态、修改的文件、测试结果。
`, { label: `execute:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    } else if (ph.layer === 'cross') {
      // 跨层 phase: 前端 + 后端并行
      const [feResult, beResult] = await parallel([
        () => agentWithRetry(`
你是 ScholarAI 的 React/TypeScript 前端工程师。${PROJECT_CONTEXT}

请执行 Phase ${ph.id} 的前端部分。

## 执行计划
${truncate(plan, 15000)}

## 重要约束
只执行与前端(apps/web/)相关的 task。跳过后端 task 并在报告中注明。

## 执行要求
1. 遵循 DESIGN_SYSTEM.md 设计规范
2. Tailwind CSS + Radix UI，TypeScript 严格类型
3. 不可变数据模式，响应式布局
4. 为新组件编写 Vitest 测试

报告修改的文件和测试结果。
`, { label: `execute-fe:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL }),
        () => agentWithRetry(`
你是 ScholarAI 的 Python/FastAPI 后端工程师。${PROJECT_CONTEXT}

请执行 Phase ${ph.id} 的后端部分。

## 执行计划
${truncate(plan, 15000)}

## 重要约束
只执行与后端(apps/api/)相关的 task。跳过前端 task 并在报告中注明。

## 执行要求
1. 遵循 apps/api 分层架构
2. Pydantic 验证、structlog 日志、pytest 测试
3. SSE 事件遵循标准类型

报告修改的文件和测试结果。
`, { label: `execute-be:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL }),
      ])
      executionResult = `## 前端执行结果\n\n${feResult}\n\n## 后端执行结果\n\n${beResult}`

    } else {
      // 前端 phase / docs phase
      executionResult = await agentWithRetry(`
你是 ScholarAI 的 React/TypeScript 前端工程师。${PROJECT_CONTEXT}

请执行 Phase ${ph.id}。

## 执行计划
${truncate(plan, 15000)}

## 执行要求
1. 遵循 DESIGN_SYSTEM.md 设计规范
2. Tailwind CSS + Radix UI，TypeScript 严格类型
3. 不可变数据模式，文件 <800 行，函数 <50 行
4. 响应式布局（320px-1920px）
5. 为新组件编写 Vitest 测试

报告每个 task 完成状态、修改的文件、测试结果。
`, { label: `execute:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })
    }

    // ── Step 6: 审查执行结果 ──────────────────────────
    log(`🔍 Step 6/8: 审查执行结果...`)

    const execReviews = await parallel(
      REVIEW_DIMENSIONS.map(d => () => agentWithRetry(`
你是 ScholarAI 的 ${d.label} 专家。${PROJECT_CONTEXT}

请审查 Phase ${ph.id} 的代码实现。

## 审查维度：${d.label}
${d.prompt}

## 执行结果（摘要）
${truncate(executionResult, 15000)}

## 输出格式（严格遵守）
VERDICT: [PASS | PASS-WITH-WARNINGS | FAIL]
CRITICAL_ISSUES: [逗号分隔，无则写 NONE]
HIGH_ISSUES: [逗号分隔，无则写 NONE]
CODE_SCORE: [1-10]
TEST_COVERAGE: [GOOD | PARTIAL | MISSING]
`, { label: `review-exec:${ph.id}:${d.key}`, phase: `Phase ${ph.id}`, model: CODE_MODEL }))
    )

    // 合成执行审查
    const execReviewSynth = await agentWithRetry(`
综合以下三个维度的审查结果，给出 Phase ${ph.id} 实现的最终评价。

## 架构审查
${truncate(execReviews[0], 8000)}

## 安全审查
${truncate(execReviews[1], 8000)}

## 性能审查
${truncate(execReviews[2], 8000)}

## 输出格式（严格遵守，必须包含 VERDICT 行）
VERDICT: [PASS | PASS-WITH-WARNINGS | FAIL]
CRITICAL_COUNT: [数字]
REWORK_ITEMS: [逗号分隔，无则写 NONE]
`, { label: `synth-exec:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })

    // 解析 CRITICAL 数量（结构化输出 + regex 兜底）
    const criticalMatch = execReviewSynth.match(/CRITICAL_COUNT:\s*(\d+)/i)
    const criticalCount = criticalMatch ? parseInt(criticalMatch[1], 10) : 0

    // 如果有 CRITICAL 问题，执行修复
    if (criticalCount > 0) {
      log(`🔧 发现 ${criticalCount} 个 CRITICAL 问题，执行修复...`)
      await agentWithRetry(`
你是 ScholarAI 的代码修复专家。${PROJECT_CONTEXT}

请修复 Phase ${ph.id} 的 CRITICAL 问题。

## 审查综合（摘要）
${truncate(execReviewSynth, 10000)}

## 修复要求
1. 只修复 CRITICAL 和 HIGH 问题
2. 每个修复后运行相关测试验证
3. 不要改变已通过审查的代码
4. 报告修改内容和测试结果
`, { label: `fix:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL })
    }

    // ── Step 7: 测试 ──────────────────────────────────
    log(`🧪 Step 7/8: 运行测试...`)

    // 顺序执行（避免共享状态竞争）
    const unitTestResult = await agentWithRetry(`
请运行 Phase ${ph.id} 相关的单元测试和集成测试。

## 后端测试
cd apps/api && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -30

## 前端测试
cd apps/web && npx vitest run --reporter=verbose 2>&1 | tail -30

## 类型检查
cd apps/web && npx tsc --noEmit 2>&1 | tail -20

报告每个检查的结果：PASS/FAIL + 失败详情。
`, { label: `test-unit:${ph.id}`, phase: `Phase ${ph.id}`, model: LIGHT_MODEL })

    const e2eTestResult = await agentWithRetry(`
请运行 Phase ${ph.id} 相关的 E2E 浏览器测试。

## Playwright 测试
cd apps/web && npx playwright test --reporter=list 2>&1 | tail -40

## 如果没有现成的 E2E 测试
1. 先阅读 apps/web/e2e/ 目录下的现有测试，理解测试模式
2. 编写至少 1 个关键路径的 E2E 测试
3. 运行测试，失败则分析原因并修复（最多重试 2 次）
4. 2 次修复后仍失败则记录原因

报告测试结果：PASS/FAIL + 截图路径（如果有）。
`, { label: `test-e2e:${ph.id}`, phase: `Phase ${ph.id}`, model: VISUAL_MODEL })  // 🔒 视觉任务：浏览器截图理解

    // ── Step 8: 更新文档 ──────────────────────────────
    log(`📝 Step 8/8: 更新文档...`)

    await agentWithRetry(`
请更新 ScholarAI 项目文档，反映 Phase ${ph.id} 的完成状态。

## 需要更新的文件
1. **${DOCS.planStatus}** - Phase ${ph.id} 状态 → done，添加完成日期
2. **${DOCS.ledger}** - 添加 DU 条目
3. **${DOCS.v5Readme}** - 更新 phase 状态
4. **创建报告** - ${reportDir()}/${today()}_v5_0_phase_${ph.slug.replace(/-/g, '_')}_closeout.md

## Phase 信息
- **ID:** ${ph.id} | **名称:** ${ph.name} | **目标:** ${ph.goal}

## 执行结果（摘要）
${truncate(executionResult, 10000)}

## 测试结果（摘要）
${truncate(unitTestResult, 5000)}

完成后报告更新了哪些文件。
`, { label: `docs:${ph.id}`, phase: `Phase ${ph.id}`, model: LIGHT_MODEL })

    // 提交 phase 完成
    await agentWithRetry(`
请提交 Phase ${ph.id} 的所有变更。

1. git add -A
2. 检查 git diff --cached --stat，如果没有变更则跳过提交
3. git commit -m "feat(v5.0-${ph.id}): complete ${ph.name}"
4. git push（失败则 git pull --rebase 后重试 1 次）

报告：提交 hash、推送状态、是否有变更。
`, { label: `commit:${ph.id}`, phase: `Phase ${ph.id}`, model: LIGHT_MODEL })

    log(`✅ Phase ${ph.id}: ${ph.name} 完成\n`)

  } catch (err) {
    log(`❌ Phase ${ph.id} 失败: ${err.message}`)
    log(`💡 使用 args.skipPhases 跳过已完成阶段后重新运行`)
    throw new Error(`Phase ${ph.id} (${ph.name}) 失败: ${err.message}`)
  }
}

// ══════════════════════════════════════════════════════════
// STAGE 2: PR 创建与合并
// ══════════════════════════════════════════════════════════
phase('PR & Merge')

log('📤 创建 Pull Request...')

const prBody = await agentWithRetry(`
请为 ScholarAI v5.0 创建 Pull Request body。

## v5.0 变更概述
ScholarAI v5.0 是"产品诚实可宣称 release-pass"的完整迭代版本。

### 10 个 Phase 交付物
${PHASES.map(p => `- **Phase ${p.id}** (${p.name}): ${p.goal}`).join('\n')}

### 关键技术变更
- 前端：设计系统 v2、WorkspaceShell v2、Upload 可视化、Read+Pretext、Notes 重构、Chat 优化
- 后端：Pipeline 稳定性、RAG SOTA、Observability

## 输出
只输出 PR body 的 Markdown 内容，不要包含其他说明。
`, { label: 'pr-body', phase: 'PR & Merge', model: CODE_MODEL })

// 创建 PR（使用 heredoc 避免 shell 注入）
await agentWithRetry(`
请使用 gh CLI 创建 Pull Request。

步骤：
1. 写入 PR body 到临时文件：
   BODY_FILE=$(mktemp)
   cat > "$BODY_FILE" << 'SCHOLAR_PR_BODY_EOF'
${prBody.substring(0, 60000)}
SCHOLAR_PR_BODY_EOF

2. 创建 PR：
   gh pr create \\
     --base main \\
     --head feat/v5-0 \\
     --title "feat(v5.0): ScholarAI v5.0 - Re-launch with UI Excellence" \\
     --body-file "$BODY_FILE" \\
     --label "v5.0,feature"

3. 清理：rm -f "$BODY_FILE"

报告 PR URL 和编号。
`, { label: 'create-pr', phase: 'PR & Merge', model: LIGHT_MODEL })

// 监视 CI
log('👀 监视 CI 测试...')

const ciResult = await agentWithRetry(`
请监视 PR 的 CI 测试状态。

## 监视流程
1. 获取 PR 编号：
   PR_NUMBER=$(gh pr view feat/v5-0 --json number -q .number)
   如果失败则报错退出。

2. 循环检查（每 30 秒，最多 30 分钟）：
   CHECKS=\$(gh pr checks "\$PR_NUMBER" --json name,state,conclusion)
   用 jq 解析：
   - FAILED=\$(echo "\$CHECKS" | jq '[.[] | select(.conclusion == "FAILURE")] | length')
   - IN_PROGRESS=\$(echo "\$CHECKS" | jq '[.[] | select(.state == "IN_PROGRESS" or .state == "QUEUING" or .conclusion == null)] | length')

3. 判断：
   - 如果 FAILED > 0，输出失败检查名称，退出
   - 如果 IN_PROGRESS == 0 且总数 > 0，全部通过

4. 如果有失败，尝试修复（最多 3 次）

## 输出格式（严格遵守）
在输出最后一行：
CI_VERDICT: ALL-PASSED
或
CI_VERDICT: FAILED
`, { label: 'monitor-ci', phase: 'PR & Merge', model: CODE_MODEL })

// 合并（使用结构化判断）
if (ciResult.includes('CI_VERDICT: ALL-PASSED')) {
  log('🎉 CI 全部通过，合并 PR...')

  await agentWithRetry(`
请合并 PR 到 main 分支。

1. PR_NUMBER=$(gh pr view feat/v5-0 --json number -q .number)
2. gh pr merge $PR_NUMBER --squash --auto
3. 等待 10 秒
4. git checkout main && git pull
5. 删除远程分支：git push origin --delete feat/v5-0
6. 删除本地分支：git branch -d feat/v5-0

报告合并结果和最终 commit hash。
`, { label: 'merge-pr', phase: 'PR & Merge', model: LIGHT_MODEL })

  log('🎊 ScholarAI v5.0 已合并到 main！')
} else {
  log('❌ CI 测试失败，需要手动检查和修复')
  log('请查看 PR 页面了解失败详情')
}

log('\n' + '═'.repeat(60))
log('🏁 ScholarAI v5.0 Full Lifecycle Workflow 完成')
log('═'.repeat(60))
