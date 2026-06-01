export const meta = {
  name: 'v5-0-full-lifecycle',
  description: 'ScholarAI v5.0 完整生命周期：10 phase 循环(研究→审查→计划→执行→测试→文档) → PR → CI 监控 → 合并',
  phases: [
    { title: 'Branch Setup', detail: '创建 feat/v5-0 分支' },
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
const VISUAL_MODEL = 'mimov2.5'
const CODE_MODEL = 'sonnet'
const LIGHT_MODEL = 'haiku'

// 跳过已完成的阶段
const SKIP_PHASES = ['5.0-0']

// 审查重试上限
const MAX_RETRIES = 3

// ══════════════════════════════════════════════════════════
// Schema 定义（结构化输出，减少 token 浪费）
// ══════════════════════════════════════════════════════════

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'PASS-WITH-WARNINGS', 'FAIL'] },
    critical_issues: { type: 'array', items: { type: 'string' } },
    high_issues: { type: 'array', items: { type: 'string' } },
    improvements: { type: 'array', items: { type: 'string' } },
    score: { type: 'number', minimum: 1, maximum: 10 },
    proceed: { type: 'boolean' },
    conditions: { type: 'string' }
  },
  required: ['verdict', 'proceed']
}

const PLAN_VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['APPROVED', 'APPROVED-WITH-CHANGES', 'NEEDS-REVISION'] },
    issues: { type: 'array', items: { type: 'string' } },
    changes_required: { type: 'array', items: { type: 'string' } },
    proceed: { type: 'boolean' }
  },
  required: ['verdict', 'proceed']
}

const EXEC_VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'PASS-WITH-WARNINGS', 'FAIL'] },
    critical_count: { type: 'number' },
    rework_items: { type: 'array', items: { type: 'string' } },
    code_score: { type: 'number', minimum: 1, maximum: 10 },
    test_coverage: { type: 'string', enum: ['GOOD', 'PARTIAL', 'MISSING'] }
  },
  required: ['verdict', 'critical_count']
}

const CI_VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['ALL-PASSED', 'FAILED', 'TIMEOUT'] },
    passed_checks: { type: 'array', items: { type: 'string' } },
    failed_checks: { type: 'array', items: { type: 'string' } },
    fix_attempts: { type: 'number' }
  },
  required: ['status']
}

// ══════════════════════════════════════════════════════════
// Phase 定义
// ══════════════════════════════════════════════════════════

const PHASES = [
  { id: '5.0-0', name: 'Foundation', slug: 'foundation', wave: 0,
    goal: '治理切换 + v4.x 迁移 + Audit Baseline，不动业务代码',
    scope: 'v4.x migration inventory, runtime contract freeze, gate input matrix, perf baseline, audit baseline',
    files: ['docs/plans/v5_0/', 'scripts/evals/run_v5_release_gate.py'],
    deps: [], layer: 'docs' },
  { id: '5.0-1', name: 'Design System v2', slug: 'design-system-v2', wave: 1,
    goal: 'CSS tokens 39→~200, oklch, dark theme, motion system, editorial typography',
    scope: 'apps/web/src/styles/, apps/web/src/components/ui/',
    files: ['apps/web/src/styles/', 'apps/web/src/components/ui/'],
    deps: ['5.0-0'], layer: 'frontend' },
  { id: '5.0-2', name: 'WorkspaceShell v2', slug: 'workspace-shell-v2', wave: 2,
    goal: '响应式 stack, Lighthouse CI, bundle budget ≤500KB, skeleton/loading/empty/error 四态',
    scope: 'apps/web/src/app/, vite.config.ts',
    files: ['apps/web/src/app/', 'apps/web/vite.config.ts'],
    deps: ['5.0-0', '5.0-1'], layer: 'frontend' },
  { id: '5.0-3', name: 'Upload Visualization', slug: 'upload-visualization', wave: 3,
    goal: 'Upload 页面路由, 拖拽+队列, SSE 进度, mid-pipeline cancel, 批量上传',
    scope: 'apps/web/src/features/uploads/, apps/api/app/api/imports/',
    files: ['apps/web/src/features/uploads/'],
    deps: ['5.0-1', '5.0-2'], layer: 'cross' },
  { id: '5.0-4', name: 'Read + Pretext', slug: 'read-pretext', wave: 4,
    goal: 'pretext 引入, PDF annotation v2, linkedNote 双向同步',
    scope: 'apps/web/src/features/read/, apps/web/src/lib/pretext/',
    files: ['apps/web/src/features/read/'],
    deps: ['5.0-1', '5.0-2'], layer: 'frontend' },
  { id: '5.0-5', name: 'Notes Refactoring', slug: 'notes-refactoring', wave: 5,
    goal: 'TipTap 二次封装, block editing, @mention pills, pretext integration',
    scope: 'apps/web/src/features/notes/',
    files: ['apps/web/src/features/notes/'],
    deps: ['5.0-1', '5.0-2', '5.0-4'], layer: 'frontend' },
  { id: '5.0-6', name: 'Chat Polish', slug: 'chat-polish', wave: 6,
    goal: 'message virtualization, composer UX, citation panel, Chat↔Notes 双向桥',
    scope: 'apps/web/src/features/chat/',
    files: ['apps/web/src/features/chat/'],
    deps: ['5.0-1', '5.0-2', '5.0-4', '5.0-5'], layer: 'frontend' },
  { id: '5.0-7', name: 'Backend Pipeline', slug: 'backend-pipeline', wave: 1,
    goal: 'upload fail-closed, auth/ownership tests, trace_id 统一, observability SLO',
    scope: 'apps/api/app/api/, apps/api/app/services/, apps/api/app/middleware/',
    files: ['apps/api/app/api/', 'apps/api/app/services/'],
    deps: ['5.0-0'], layer: 'backend' },
  { id: '5.0-8', name: 'RAG SOTA', slug: 'rag-sota', wave: 2,
    goal: 'RAPTOR-lite, review-only Graph synthesis, verifier fusion + NLI',
    scope: 'apps/api/app/rag_v3/, apps/api/app/services/',
    files: ['apps/api/app/rag_v3/'],
    deps: ['5.0-0', '5.0-7'], layer: 'backend' },
  { id: '5.0-9', name: 'Release Gate', slug: 'release-gate', wave: 9,
    goal: '7 E2E journeys, consolidated gate runner, multidimensional audit, release verdict',
    scope: 'scripts/evals/, apps/web/e2e/',
    files: ['scripts/evals/', 'apps/web/e2e/'],
    deps: ['5.0-0', '5.0-1', '5.0-2', '5.0-3', '5.0-4', '5.0-5', '5.0-6', '5.0-7', '5.0-8'], layer: 'acceptance' },
]

// 审查维度（动态注入，不硬编码角色）
const REVIEW_DIMENSIONS = [
  { key: 'arch', focus: '架构分层、模块耦合、接口设计、依赖方向、代码边界' },
  { key: 'security', focus: 'OWASP Top 10、输入验证、认证授权、密钥管理、数据泄露' },
  { key: 'perf', focus: 'Core Web Vitals、bundle 体积、内存泄漏、N+1 查询、a11y 合规' },
]

// ══════════════════════════════════════════════════════════
// 工具函数
// ══════════════════════════════════════════════════════════

function truncate(str, maxLen = 30000) {
  if (!str) return '[empty]'
  if (str.length <= maxLen) return str
  const half = Math.floor(maxLen / 2)
  return str.substring(0, half) + `\n\n[... 省略 ${str.length - maxLen} 字符 ...]\n\n` + str.substring(str.length - half)
}

function isTransientError(err) {
  const msg = (err.message || '').toLowerCase()
  return msg.includes('rate limit') || msg.includes('timeout')
    || msg.includes('503') || msg.includes('529')
    || msg.includes('overloaded') || msg.includes('econnreset')
}

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
      log(`⚠️ ${label} 失败 (${attempt}/${maxRetries}), ${delay}ms 后重试`)
      await new Promise(r => setTimeout(r, delay))
    }
  }
  throw lastError
}

// 带容错的 parallel（一个失败不影响其他）
async function parallelSafe(tasks) {
  const results = await parallel(
    tasks.map(fn => () => fn().catch(e => ({ error: e.message, verdict: 'FAIL', proceed: false })))
  )
  return results
}

// ══════════════════════════════════════════════════════════
// 提示词模板（动态组装，不硬编码角色）
// ══════════════════════════════════════════════════════════

const CONTEXT = `ScholarAI：学术论文智能阅读系统。
技术栈：React 18 + TypeScript + Vite | Python FastAPI | PostgreSQL + PGVector + Neo4j + Redis
约束：apps/web = 前端唯一路径，apps/api = 后端唯一路径。
规范：不可变数据、函数 <50 行、文件 <800 行、TypeScript 严格类型。`

function researchPrompt(ph) {
  return `## 任务：深度研究 Phase ${ph.id} (${ph.name})

## 目标
${ph.goal}

## 范围
${ph.scope}

## 涉及文件
${ph.files.join(', ')}

## 依赖
${ph.deps.length > 0 ? ph.deps.join(', ') : '无（起点）'}

## 要求
1. 读取涉及的文件/目录，理解现有实现状态
2. 确定技术方案、库、工具
3. 当前代码与目标之间的差距
4. 技术风险、依赖风险、范围风险
5. 按子任务拆分，估计复杂度

## 上下文
${CONTEXT}

输出结构化研究报告：现状分析、技术方案、子任务拆分、风险清单、依赖映射、工作量估计。`
}

function reviewPrompt(ph, dimension, content) {
  return `## 任务：审查 Phase ${ph.id} (${ph.name}) 的研究报告

## 审查焦点
${dimension.focus}

## 审查对象
${truncate(content, 20000)}

## 上下文
${CONTEXT}

## 输出要求
返回 JSON：{ "verdict": "PASS|PASS-WITH-WARNINGS|FAIL", "critical_issues": [...], "high_issues": [...], "improvements": [...], "proceed": true/false, "conditions": "..." }`
}

function synthPrompt(ph, reviews) {
  return `## 任务：综合审查结果，判断 Phase ${ph.id} (${ph.name}) 是否可以进入计划阶段

## 三维审查结果
### 架构审查
${truncate(reviews[0], 8000)}

### 安全审查
${truncate(reviews[1], 8000)}

### 性能审查
${truncate(reviews[2], 8000)}

## 输出要求
返回 JSON：{ "verdict": "PASS|PASS-WITH-WARNINGS|FAIL", "critical_issues": [...], "proceed": true/false, "conditions": "..." }`
}

function fixResearchPrompt(ph, issues, original) {
  return `## 任务：修复 Phase ${ph.id} (${ph.name}) 研究报告中的问题

## 审查发现的问题
${truncate(issues, 5000)}

## 原始研究报告
${truncate(original, 15000)}

## 上下文
${CONTEXT}

## 要求
1. 修正所有 critical_issues 和 high_issues
2. 确保状态声明与实际代码库一致
3. 保持报告整体结构不变

输出修正后的完整研究报告。`
}

function planPrompt(ph, research, reviewSynth) {
  return `## 任务：为 Phase ${ph.id} (${ph.name}) 生成执行计划

## 目标
${ph.goal}

## 范围
${ph.scope}

## 层
${ph.layer}（frontend/backend/cross/docs）

## 研究报告（摘要）
${truncate(research, 15000)}

## 审查结论
${truncate(reviewSynth, 5000)}

## 上下文
${CONTEXT}

## 输出格式
1. **Objective**: 清晰目标
2. **Tasks**: 每个 task 含 name / files / action / verify / done / type
3. **Wave 分组**: 按依赖关系分波
4. **Success Criteria**: 可衡量验收标准

每个 plan 最多 3 个 task，action 要具体可执行。`
}

function planReviewPrompt(ph, plan) {
  return `## 任务：审查 Phase ${ph.id} (${ph.name}) 执行计划

## 目标
${ph.goal}

## 执行计划（摘要）
${truncate(plan, 15000)}

## 审查维度
1. 完整性：是否覆盖 phase 目标？
2. 可行性：task action 是否具体可执行？
3. 依赖正确性：wave 分组是否合理？
4. 可验证性：verify 命令能否实际验证？
5. 范围控制：是否有范围蔓延？

## 输出要求
返回 JSON：{ "verdict": "APPROVED|APPROVED-WITH-CHANGES|NEEDS-REVISION", "issues": [...], "changes_required": [...], "proceed": true/false }`
}

function fixPlanPrompt(ph, review, original) {
  return `## 任务：修复 Phase ${ph.id} (${ph.name}) 执行计划

## 审查发现的问题
${truncate(review, 3000)}

## 原始执行计划
${truncate(original, 10000)}

## 上下文
${CONTEXT}

## 要求
1. 修正所有 changes_required
2. 保持计划整体结构和目标不变
3. 确保每个 task 的 action 具体可执行

输出修正后的完整执行计划。`
}

function executePrompt(ph, plan) {
  const layerInstructions = {
    frontend: `你是前端工程师。只执行与 apps/web/ 相关的 task，跳过后端 task。
要求：遵循 DESIGN_SYSTEM.md、Tailwind + Radix UI、TypeScript 严格类型、不可变数据、响应式布局、Vitest 测试。`,
    backend: `你是后端工程师。只执行与 apps/api/ 相关的 task，跳过前端 task。
要求：遵循分层架构、Pydantic 验证、structlog 日志、pytest 测试。`,
    cross: null, // 特殊处理
    docs: `你负责文档和治理。只修改 docs/ 和 scripts/ 目录。`,
    acceptance: `你是验收测试工程师。运行 E2E 测试、Release Gate、治理检查、Bundle 检查。`
  }

  const instruction = layerInstructions[ph.layer] || layerInstructions.frontend

  return `## 任务：执行 Phase ${ph.id} (${ph.name})

## 执行计划
${truncate(plan, 15000)}

## 角色
${instruction}

## 上下文
${CONTEXT}

## 输出
报告每个 task 完成状态、修改的文件、测试结果。`
}

function crossExecutePrompt(ph, plan, layer) {
  const isFrontend = layer === 'frontend'
  return `## 任务：执行 Phase ${ph.id} (${ph.name}) 的${isFrontend ? '前端' : '后端'}部分

## 执行计划
${truncate(plan, 15000)}

## 约束
只执行与${isFrontend ? '前端(apps/web/)' : '后端(apps/api/)'}相关的 task。跳过其他 task 并在报告中注明。

## 角色
${isFrontend
  ? '前端工程师。要求：DESIGN_SYSTEM.md、Tailwind + Radix UI、TypeScript、不可变数据、Vitest 测试。'
  : '后端工程师。要求：分层架构、Pydantic 验证、structlog 日志、pytest 测试。'}

## 上下文
${CONTEXT}

输出修改的文件和测试结果。`
}

function execReviewPrompt(ph, dimension, result) {
  return `## 任务：审查 Phase ${ph.id} (${ph.name}) 的代码实现

## 审查焦点
${dimension.focus}

## 执行结果（摘要）
${truncate(result, 15000)}

## 上下文
${CONTEXT}

## 输出要求
返回 JSON：{ "verdict": "PASS|PASS-WITH-WARNINGS|FAIL", "critical_issues": [...], "high_issues": [...], "code_score": 1-10, "test_coverage": "GOOD|PARTIAL|MISSING" }`
}

function execSynthPrompt(ph, reviews) {
  return `## 任务：综合审查结果，判断 Phase ${ph.id} (${ph.name}) 实现是否通过

## 三维审查结果
### 架构审查
${truncate(reviews[0], 8000)}

### 安全审查
${truncate(reviews[1], 8000)}

### 性能审查
${truncate(reviews[2], 8000)}

## 输出要求
返回 JSON：{ "verdict": "PASS|PASS-WITH-WARNINGS|FAIL", "critical_count": N, "rework_items": [...], "code_score": 1-10 }`
}

function fixExecPrompt(ph, review) {
  return `## 任务：修复 Phase ${ph.id} (${ph.name}) 的 CRITICAL 问题

## 审查综合（摘要）
${truncate(review, 10000)}

## 上下文
${CONTEXT}

## 要求
1. 只修复 critical_count > 0 的问题
2. 每个修复后运行相关测试验证
3. 不要改变已通过审查的代码

报告修改内容和测试结果。`
}

function unitTestPrompt(ph) {
  return `## 任务：运行 Phase ${ph.id} (${ph.name}) 的单元测试

## 后端测试
cd apps/api && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -30

## 前端测试
cd apps/web && npx vitest run --reporter=verbose 2>&1 | tail -30

## 类型检查
cd apps/web && npx tsc --noEmit 2>&1 | tail -20

报告每个检查的结果：PASS/FAIL + 失败详情。`
}

function e2eTestPrompt(ph) {
  return `## 任务：运行 Phase ${ph.id} (${ph.name}) 的 E2E 浏览器测试

## Playwright 测试
cd apps/web && npx playwright test --reporter=list 2>&1 | tail -40

## 如果没有现成的 E2E 测试
1. 先阅读 apps/web/e2e/ 目录下的现有测试，理解测试模式
2. 编写至少 1 个关键路径的 E2E 测试
3. 运行测试，失败则分析原因并修复（最多重试 2 次）

报告测试结果：PASS/FAIL + 截图路径（如果有）。`
}

function docsPrompt(ph, execResult, testResult) {
  const date = typeof args !== 'undefined' && args?.date ? args.date : '2026-05-31'
  return `## 任务：更新文档，反映 Phase ${ph.id} (${ph.name}) 的完成状态

## 需要更新的文件
1. **docs/plans/PLAN_STATUS.md** - Phase ${ph.id} 状态 → done
2. **docs/specs/governance/phase-delivery-ledger.md** - 添加 DU 条目
3. **docs/plans/v5_0/README.md** - 更新 phase 状态
4. **创建报告** - docs/plans/v5_0/reports/${date}_v5_0_phase_${ph.slug.replace(/-/g, '_')}_closeout.md

## 执行结果（摘要）
${truncate(execResult, 10000)}

## 测试结果（摘要）
${truncate(testResult, 5000)}

完成后报告更新了哪些文件。`
}

function commitPrompt(ph) {
  return `## 任务：提交 Phase ${ph.id} (${ph.name}) 的所有变更

1. git add -A
2. 检查 git diff --cached --stat，如果没有变更则跳过提交
3. git commit -m "feat(v5.0-${ph.id}): complete ${ph.name}"
4. git push（失败则 git pull --rebase 后重试 1 次）

报告：提交 hash、推送状态、是否有变更。`
}

// ══════════════════════════════════════════════════════════
// 审查循环（核心模式：审查→修复→重审，直到通过或耗尽重试）
// ══════════════════════════════════════════════════════════

async function reviewWithFixLoop({ ph, content, reviewFn, fixFn, synthFn, label }) {
  let current = content
  let passed = false

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    // 并行三维审查
    const reviews = await parallelSafe(
      REVIEW_DIMENSIONS.map(d => () =>
        agentWithRetry(reviewFn(current, d), {
          label: `${label}:${d.key}:${attempt}`,
          phase: `Phase ${ph.id}`,
          model: CODE_MODEL,
          schema: VERDICT_SCHEMA
        })
      )
    )

    // 综合审查
    const synth = await agentWithRetry(synthFn(reviews), {
      label: `synth-${label}:${attempt}`,
      phase: `Phase ${ph.id}`,
      model: CODE_MODEL,
      schema: VERDICT_SCHEMA
    })

    if (synth.proceed) {
      log(`✅ ${label} 审查通过`)
      return { passed: true, result: current, synth }
    }

    log(`⚠️ ${label} 审查未通过 (尝试 ${attempt + 1}/${MAX_RETRIES}): ${synth.conditions || '未知'}`)

    if (attempt < MAX_RETRIES - 1) {
      log(`🔧 修复 ${label}...`)
      current = await agentWithRetry(fixFn(synth, current), {
        label: `fix-${label}:${attempt}`,
        phase: `Phase ${ph.id}`,
        model: CODE_MODEL
      })
      log(`✅ ${label} 已修正`)
    }
  }

  throw new Error(`Phase ${ph.id} ${label} 在 ${MAX_RETRIES} 次重试后仍未通过`)
}

// ══════════════════════════════════════════════════════════
// STAGE 0: 分支创建
// ══════════════════════════════════════════════════════════
phase('Branch Setup')

log('🌿 创建 feat/v5-0 分支...')

await agentWithRetry(`## 任务：准备 Git 分支

1. 确认当前分支状态和工作区是否干净
2. 如果有未提交的 v5.0 相关文件，先提交
3. 从 main 创建新分支 feat/v5-0（如果已存在则切换过去）
4. 推送到远程：git push -u origin feat/v5-0

报告：当前分支名、最新 commit hash、工作区状态。`, {
  label: 'branch-setup',
  phase: 'Branch Setup',
  model: LIGHT_MODEL
})

log('✅ 分支 feat/v5-0 就绪')

// ══════════════════════════════════════════════════════════
// STAGE 1: 逐 Phase 执行循环
// ══════════════════════════════════════════════════════════

for (const ph of PHASES) {
  if (SKIP_PHASES.includes(ph.id)) {
    log(`⏭️ 跳过 Phase ${ph.id}（已完成）`)
    continue
  }

  phase(`Phase ${ph.id}`)

  log(`\n${'═'.repeat(60)}`)
  log(`📦 Phase ${ph.id}: ${ph.name}`)
  log(`🎯 ${ph.goal}`)
  log(`${'═'.repeat(60)}\n`)

  try {
    // ── Step 1: 研究 ─────────────────────────────────
    log(`📚 Step 1/8: 研究...`)

    let research = await agentWithRetry(researchPrompt(ph), {
      label: `research:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: CODE_MODEL
    })

    if (!research || research.length < 200) {
      throw new Error(`研究输出不足 (${research?.length || 0} 字符)`)
    }

    // ── Step 2: 审查研究（循环修复） ──────────────────
    log(`🔍 Step 2/8: 审查研究...`)

    const researchResult = await reviewWithFixLoop({
      ph,
      content: research,
      reviewFn: (content, dim) => reviewPrompt(ph, dim, content),
      fixFn: (issues, original) => fixResearchPrompt(ph, issues, original),
      synthFn: (reviews) => synthPrompt(ph, reviews),
      label: '研究'
    })
    research = researchResult.result

    // ── Step 3: 生成执行计划 ──────────────────────────
    log(`📋 Step 3/8: 生成执行计划...`)

    let plan = await agentWithRetry(planPrompt(ph, research, JSON.stringify(researchResult.synth)), {
      label: `plan:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: CODE_MODEL
    })

    // ── Step 4: 审查计划（循环修复） ──────────────────
    log(`🔍 Step 4/8: 审查计划...`)

    let planPassed = false
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      const planReview = await agentWithRetry(planReviewPrompt(ph, plan), {
        label: `review-plan:${attempt}`,
        phase: `Phase ${ph.id}`,
        model: CODE_MODEL,
        schema: PLAN_VERDICT_SCHEMA
      })

      if (planReview.proceed) {
        planPassed = true
        log(`✅ 计划审查通过`)
        break
      }

      log(`⚠️ 计划需要修订 (尝试 ${attempt + 1}/${MAX_RETRIES})`)
      if (attempt < MAX_RETRIES - 1) {
        plan = await agentWithRetry(fixPlanPrompt(ph, JSON.stringify(planReview), plan), {
          label: `fix-plan:${attempt}`,
          phase: `Phase ${ph.id}`,
          model: CODE_MODEL
        })
        log(`✅ 计划已修正`)
      }
    }

    if (!planPassed) {
      throw new Error(`执行计划在 ${MAX_RETRIES} 次重试后仍未通过`)
    }

    // ── Step 5: 执行 ──────────────────────────────────
    log(`⚡ Step 5/8: 执行...`)

    let executionResult

    if (ph.layer === 'cross') {
      const [feResult, beResult] = await parallelSafe([
        () => agentWithRetry(crossExecutePrompt(ph, plan, 'frontend'), {
          label: `execute-fe:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL
        }),
        () => agentWithRetry(crossExecutePrompt(ph, plan, 'backend'), {
          label: `execute-be:${ph.id}`, phase: `Phase ${ph.id}`, model: CODE_MODEL
        })
      ])
      executionResult = `## 前端\n\n${feResult}\n\n## 后端\n\n${beResult}`
    } else {
      executionResult = await agentWithRetry(executePrompt(ph, plan), {
        label: `execute:${ph.id}`,
        phase: `Phase ${ph.id}`,
        model: CODE_MODEL
      })
    }

    // ── Step 6: 审查执行结果（循环修复） ──────────────
    log(`🔍 Step 6/8: 审查执行结果...`)

    const execResult = await reviewWithFixLoop({
      ph,
      content: executionResult,
      reviewFn: (content, dim) => execReviewPrompt(ph, dim, content),
      fixFn: (issues, _) => fixExecPrompt(ph, JSON.stringify(issues)),
      synthFn: (reviews) => execSynthPrompt(ph, reviews),
      label: '执行'
    })

    // ── Step 7: 测试 ──────────────────────────────────
    log(`🧪 Step 7/8: 运行测试...`)

    // 顺序执行（避免共享状态竞争）
    const unitTestResult = await agentWithRetry(unitTestPrompt(ph), {
      label: `test-unit:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: LIGHT_MODEL
    })

    const e2eTestResult = await agentWithRetry(e2eTestPrompt(ph), {
      label: `test-e2e:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: VISUAL_MODEL  // 🔒 视觉任务
    })

    // ── Step 8: 更新文档 ──────────────────────────────
    log(`📝 Step 8/8: 更新文档...`)

    await agentWithRetry(docsPrompt(ph, executionResult, unitTestResult), {
      label: `docs:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: LIGHT_MODEL
    })

    await agentWithRetry(commitPrompt(ph), {
      label: `commit:${ph.id}`,
      phase: `Phase ${ph.id}`,
      model: LIGHT_MODEL
    })

    log(`✅ Phase ${ph.id}: ${ph.name} 完成\n`)

  } catch (err) {
    log(`❌ Phase ${ph.id} 失败: ${err.message}`)
    throw new Error(`Phase ${ph.id} (${ph.name}) 失败: ${err.message}`)
  }
}

// ══════════════════════════════════════════════════════════
// STAGE 2: PR 创建与合并
// ══════════════════════════════════════════════════════════
phase('PR & Merge')

log('📤 创建 Pull Request...')

const prBody = await agentWithRetry(`## 任务：为 ScholarAI v5.0 创建 Pull Request body

### 10 个 Phase 交付物
${PHASES.map(p => `- **Phase ${p.id}** (${p.name}): ${p.goal}`).join('\n')}

### 关键技术变更
- 前端：设计系统 v2、WorkspaceShell v2、Upload 可视化、Read+Pretext、Notes 重构、Chat 优化
- 后端：Pipeline 稳定性、RAG SOTA、Observability

只输出 PR body 的 Markdown 内容。`, {
  label: 'pr-body',
  phase: 'PR & Merge',
  model: CODE_MODEL
})

// 创建 PR（heredoc 避免 shell 注入）
await agentWithRetry(`## 任务：使用 gh CLI 创建 Pull Request

步骤：
1. 写入 PR body 到临时文件：
   BODY_FILE=$(mktemp)
   cat > "$BODY_FILE" << 'SCHOLAR_PR_EOF'
${prBody.substring(0, 60000)}
SCHOLAR_PR_EOF

2. 创建 PR：
   gh pr create --base main --head feat/v5-0 --title "feat(v5.0): ScholarAI v5.0 - Re-launch with UI Excellence" --body-file "$BODY_FILE" --label "v5.0,feature"

3. 清理：rm -f "$BODY_FILE"

报告 PR URL 和编号。`, {
  label: 'create-pr',
  phase: 'PR & Merge',
  model: LIGHT_MODEL
})

// 监视 CI
log('👀 监视 CI 测试...')

const ciResult = await agentWithRetry(`## 任务：监视 PR 的 CI 测试状态

1. 获取 PR 编号：PR_NUMBER=$(gh pr view feat/v5-0 --json number -q .number)
2. 循环检查（每 30 秒，最多 30 分钟）：
   CHECKS=$(gh pr checks "$PR_NUMBER" --json name,state,conclusion)
   用 jq 解析：FAILED=$(echo "$CHECKS" | jq '[.[] | select(.conclusion == "FAILURE")] | length')
3. 判断：FAILED > 0 则失败；IN_PROGRESS == 0 且总数 > 0 则通过
4. 如果有失败，尝试修复（最多 3 次）

返回 JSON：{ "status": "ALL-PASSED|FAILED|TIMEOUT", "passed_checks": [...], "failed_checks": [...] }`, {
  label: 'monitor-ci',
  phase: 'PR & Merge',
  model: CODE_MODEL,
  schema: CI_VERDICT_SCHEMA
})

// 合并
if (ciResult.status === 'ALL-PASSED') {
  log('🎉 CI 全部通过，合并 PR...')

  await agentWithRetry(`## 任务：合并 PR 到 main 分支

1. PR_NUMBER=$(gh pr view feat/v5-0 --json number -q .number)
2. gh pr merge $PR_NUMBER --squash --auto
3. 等待 10 秒
4. git checkout main && git pull
5. 删除远程分支：git push origin --delete feat/v5-0
6. 删除本地分支：git branch -d feat/v5-0

报告合并结果和最终 commit hash。`, {
    label: 'merge-pr',
    phase: 'PR & Merge',
    model: LIGHT_MODEL
  })

  log('🎊 ScholarAI v5.0 已合并到 main！')
} else {
  log('❌ CI 测试失败，需要手动检查和修复')
}

log('\n' + '═'.repeat(60))
log('🏁 ScholarAI v5.0 Full Lifecycle Workflow 完成')
log('═'.repeat(60))
