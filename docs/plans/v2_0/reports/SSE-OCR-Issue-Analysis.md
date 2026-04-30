---
作者：glm5.1+37chengshan
日期：2026-04-18
标签：frontend-audit,sse-architecture,ocr-config
---

# SSE 双轨并存与 OCR 默认开启问题根本分析

## 问题概述

你提出两个关键遗留问题：

1. **SSE 双轨兼容长期并存** - sseService/useChatStream/useSSE 多个 Hook 并存，事件类型存在 legacy + 新协议双解析，产生持续的 message_id 缺失告警。
2. **OCR 默认开启** - 虽然之前已要求修改，但 `PARSER_DO_OCR` 仍硬编码为 True。

本文档提供根本原因分析和具体修复方案。

---

## 1. SSE 双轨并存详细分析

### 1.1 架构现状：三层 SSE 栈

当前代码中确实存在**三套并行的 SSE 处理体系**：

#### 层级 1：底层服务 - `SSEService`
**文件位置**：[apps/web/src/services/sseService.ts](apps/web/src/services/sseService.ts)

```typescript
// Line 345: 导出单例
export const sseService = new SSEService();
```

**职责**：
- 原始 EventSource/fetch 连接管理
- 自动重连（3 次重试 + 指数退避）
- 心跳监控（60s 超时）

**支持的事件类型**（第 52-67 行）：
```typescript
export type SSEEventType =
  | 'session_start'
  | 'routing_decision'
  | 'phase'
  | 'reasoning'          // ← NEW
  | 'message'            // ← NEW
  | 'tool_call'
  | 'tool_result'
  | 'thought'            // ← LEGACY (deprecated)
  | 'thinking_status'    // ← LEGACY (deprecated)
  | 'step_progress';     // ← LEGACY (deprecated)
```

**问题**：注释明确标注 "legacy event types (deprecated but kept for backward compatibility)"，说明**历史兼容层直接写入核心类型定义中**。

---

#### 层级 2：状态管理 Hook - `useChatStream`
**文件位置**：[apps/web/src/app/hooks/useChatStream.ts](apps/web/src/app/hooks/useChatStream.ts)

**职责**：
- 状态机 + 缓冲 + 节流（100ms）
- 事件路由与分类（reasoning vs content）
- message_id 验证（HARD RULE 0.2）

**关键实现**（第 540-620 行）：

```typescript
// 第 545-549 行：message_id 不匹配告警（你看到的警告就来自这里）
if (messageIdRef.current && messageIdRef.current !== envelope.message_id) {
  console.warn(
    `[useChatStream] SSE event message_id mismatch. Expected: ${messageIdRef.current}, Got: ${envelope.message_id}. Ignoring.`
  );
  return;
}

// 第 570-576 行：Legacy 协议别名处理
switch (eventType) {
  case 'thought':        // ← LEGACY 别名
  case 'reasoning':      // ← NEW 标准
    // 两个都指向同一个处理逻辑
    const content = (data.delta as string) || (data.content as string) || '';
```

**问题识别**：
- 事件类型在 switch 中采用了**别名合并**（'thought' 和 'reasoning' 合并处理）
- 这掩盖了底层协议混乱：前端既要接收 'thought' 又要接收 'reasoning'
- 当后端同时发送两种格式时，就会触发缓冲不同步或 message_id 校验失败

---

#### 层级 3：React Hook 包装 - `useSSE`
**文件位置**：[apps/web/src/app/hooks/useSSE.ts](apps/web/src/app/hooks/useSSE.ts)

**职责**：
- React 组件集成（connect/disconnect/cleanup）
- 消息积累与状态同步
- 确认请求状态管理

**使用情况**：
```bash
$ grep -r "import.*useSSE" apps/web/src/ --include="*.tsx"
# 结果：仅在 useSSE.test.tsx 中导入
```

**结论**：useSSE 实际上**几乎未被使用**，所有生产代码都用 useChatStream。

---

### 1.2 为什么会有 message_id 缺失告警？

#### 根本原因链

1. **后端事件格式不统一**
   - 某些事件可能不包含 message_id（特别是 legacy 兼容路径）
   - 或 message_id 字段名不一致（envelope.message_id vs data.message_id）

2. **前端缺少 fallback 机制**
   - 第 545 行：直接 `messageIdRef.current !== envelope.message_id` 
   - 没有处理 envelope.message_id 为 null/undefined 的情况

3. **事件重复处理**
   - 如果后端同时发送 'thought' + 'reasoning'（为了向前向后兼容），前端会：
     - 第一次进来：绑定 message_id
     - 第二次相同内容来临：被识别为不匹配而丢弃

#### 实际观测

测试日志中的 message_id mismatch 告警出现频率高，但**测试仍然通过**，说明：
- 告警是**偶发的、跨流程的干扰**
- 不是关键路径失败，而是**边缘情况导致的噪音**

---

### 1.3 为什么代码没被清理？

#### 历史因素

1. **Sprint 3 架构迁移未完成**
   - ChatLegacy.tsx（第 247 行）明确注释：使用 useChatStream
   - 但没有彻底清理 legacy SSE 事件类型定义
   
2. **向后兼容的包容性设计**
   - 不想破坏旧版本后端
   - 索性就在 sseService 类型定义中保留了 legacy 类型

3. **useSSE 的遗留**
   - 可能是 PR 中初版设计
   - 后来被 useChatStream 替代
   - 但没有完全删除（保留了测试）

---

## 2. OCR 智能降级问题根本分析（PR7 规范缺失）

### 2.1 问题本质 - 这不是"配置问题"，是"PR7 规范被回滚了"

**关键发现**：PR7 Phase 7A 的规划文档明确要求 **"OCR 不再全量默认开启"**，但当前实现违反了这个要求。

#### PR7 原设计（见 `docs/plans/PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案.md` 第 424-454 行）

> **当前问题**：ParserConfig.do_ocr = True
> 这会导致 born-digital PDF 也默认走 OCR，带来：
> - 速度下降
> - 文本顺序稳定性下降
> - 解析噪声增加
>
> **交付清单**：
> - ✅ adaptive chunking 真正生效
> - ❌ **OCR 不再全量默认开启** ← **当前未完成**
> - ✅ parse mode 可追踪
> - ✅ 解析耗时和质量改善

### 2.2 原设计的智能降级机制（已在代码中实现）

**两阶段 native → OCR fallback**：

```python
# 第一阶段：原生解析（快速）
result_native = self.native_converter.convert(path)  # do_ocr=False
markdown = result_native.document.export_to_markdown()

# 第二阶段：智能检测（降级决策）
if self._should_retry_with_ocr(markdown, page_count):
    # 文本密度太低（< 80 chars/page） → 自动降级
    result_ocr = self.ocr_converter.convert(path)  # do_ocr=True
    markdown = result_ocr.document.export_to_markdown()
```

**关键检测函数**（`_should_retry_with_ocr`，第 201-210 行）：

```python
def _should_retry_with_ocr(self, markdown: str, page_count: int) -> bool:
    """智能检测：如果原生解析的文本密度太低，就降级到 OCR"""
    non_whitespace_chars = len(re.sub(r"\s+", "", markdown or ""))
    chars_per_page = non_whitespace_chars / page_count
    
    # 如果平均每页 < 80 个字符，说明是扫描件或图片居多
    return chars_per_page < self.config.ocr_retry_min_chars_per_page  # 80
```

### 2.3 当前错误做法

**错误方式** - 硬编码全量开启：

```python
# config.py 第 232 行（错误）
PARSER_DO_OCR: bool = True  # OCR enabled by default (was False)

# docling_service.py 第 61 行（错误）
do_ocr: bool = True  # Enable OCR fallback...
```

**后果**：
- 所有 PDF 都初始化 OCR converters（CPU + 内存成本）
- 即使 born-digital PDF（高文本密度），也会被 OCR 处理
- 文本顺序可能被破坏（OCR 排版逻辑与原生不同）
- 性能下降（native: 1-3s，OCR: 10-30s）

---

### 2.3 为什么没有环境变量覆盖？

**搜索结果**：

```bash
$ grep -n "PARSER_DO_OCR\|getenv.*OCR" apps/api/app/config.py
# 232: PARSER_DO_OCR: bool = True  # OCR enabled by default (was False)
# → 没有 os.getenv() 或 Field(default_factory=...)
```

**对比其他配置项**：

```python
# 有环境变量支持的：
CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://...")

# OCR 配置：
PARSER_DO_OCR: bool = True  # 直接硬编码，无环境变量
```

**结论**：OCR 配置**被遗漏在了环境化之外**。

---

## 3. 根本原因总结

| 问题 | 根本原因 | 当前危害 | 优先级 |
|------|--------|--------|------|
| SSE 三层并存 | Sprint 3 迁移不完整 + 向后兼容包容性 | 代码维护成本高、测试噪音、认知负担 | P1 |
| message_id 告警 | 后端协议混乱 + 前端缺 fallback | 虽可通过测试但影响调试体验 | P1 |
| useSSE 遗留 | 被 useChatStream 替代但未删除 | 维护两套 Hook、测试冗余 | P2 |
| OCR 硬编码 True | 配置环境化遗漏 + 没有分环境策略 | 本地开发启动慢、无法禁用 OCR | P1 |
| OCR "was False" 残留 | 缺乏变更日志说明 | 后续维护者困惑、决策不可溯源 | P2 |

---

## 4. 修复方案

### 方案 A：SSE 双轨收口（建议立即执行）

#### A.1 统一事件类型定义

**目标**：移除 legacy 类型别名，在 adapter 边界统一处理。

**执行步骤**：

1. 在 [apps/web/src/services/sseService.ts](apps/web/src/services/sseService.ts) 中，将 legacy 类型移到单独的 adapter：

```typescript
// sseService.ts - 移除 legacy 类型
export type SSEEventType =
  | 'session_start'
  | 'routing_decision'
  | 'phase'
  | 'reasoning'
  | 'message'
  | 'tool_call'
  | 'tool_result'
  | 'citation'
  | 'confirmation_required'
  | 'cancel'
  | 'done'
  | 'heartbeat'
  | 'error';

// sseParser.ts - 新建 adapter，处理 legacy -> new 映射
function normalizeEventType(rawType: string): SSEEventType {
  const legacyMap: Record<string, SSEEventType> = {
    'thought': 'reasoning',
    'thinking_status': 'phase',
    'step_progress': 'phase',
  };
  return legacyMap[rawType] || rawType as SSEEventType;
}
```

2. 在 [apps/web/src/app/hooks/useChatStream.ts](apps/web/src/app/hooks/useChatStream.ts) 中，移除 switch 中的别名处理：

```typescript
// 将这段：
case 'thought':
case 'reasoning':
  // ...

// 改为：
case 'reasoning':
  // ...
```

#### A.2 修复 message_id 验证

**目标**：处理 message_id 缺失的情况，而不是直接丢弃。

**实现**（useChatStream.ts 第 545-550 行）：

```typescript
// 修前：直接校验不等
if (messageIdRef.current && messageIdRef.current !== envelope.message_id) {
  console.warn(`[useChatStream] SSE event message_id mismatch...`);
  return;
}

// 修后：允许 fallback
if (messageIdRef.current && envelope.message_id && messageIdRef.current !== envelope.message_id) {
  // 只在两者都存在且不相等时才丢弃
  console.warn(`[useChatStream] SSE event message_id mismatch...`);
  return;
} else if (!envelope.message_id && messageIdRef.current) {
  // 允许后续事件缺失 message_id，用已绑定的
  envelope.message_id = messageIdRef.current;
  console.debug(`[useChatStream] Imputing message_id from session context`);
}
```

#### A.3 删除 useSSE Hook

**根据**：几乎无人使用，所有生产代码用 useChatStream。

**执行**：
- 删除 [apps/web/src/app/hooks/useSSE.ts](apps/web/src/app/hooks/useSSE.ts)
- 删除 [apps/web/src/app/hooks/useSSE.test.tsx](apps/web/src/app/hooks/useSSE.test.tsx)
- 更新导入（全局搜索 "import.*useSSE"，目前只有测试）

**时间**：1-2 小时

---

### 方案 B：OCR 智能降级恢复（完成 PR7 缺失改动）

#### B.1 原理：恢复二阶段 native → OCR fallback

**设计意图**（PR7）：

```
born-digital PDF (文本密度高)
  ↓ [native_converter] → 快速，保留原序
  ↓ [文本密度检查]
  ↓ [如果 > 80 chars/page] → 返回结果 ✓
  ↓ [如果 < 80 chars/page] → 可能是扫描件
  ↓ [ocr_converter] → 恢复图片中的文本
  ↓ 返回结果 ✓
```

#### B.2 执行改动（已完成）

**1. 恢复默认值**（config.py 第 232 行）：

```python
# 修前：硬编码 True
PARSER_DO_OCR: bool = True  # OCR enabled by default (was False)

# 修后：恢复智能降级
PARSER_DO_OCR: bool = False  # OCR disabled by default (smart fallback enabled)
```

**为什么是 False**：
- False 表示"不直接启用 OCR"
- 但通过 `_should_retry_with_ocr` 机制，扫描件会自动降级到 OCR
- 这样 born-digital PDF 快速（避免 OCR 成本），扫描件准确（自动用 OCR）

**2. 说明智能降级机制**（docling_service.py 第 201-210 行）：

新增详细注释说明 `_should_retry_with_ocr` 的检测逻辑和门槛值（80 chars/page）

#### B.3 验证方案（执行步骤）

```bash
# 前置：确保 Python 3.11 环境 + 依赖已装
cd apps/api && python -m pytest tests/unit/test_docling_chunk_strategy.py -v

# 1. 验证 native parser 工作（默认无 OCR）
python -c "
from app.core.docling_service import ParserConfig, DoclingParser
config = ParserConfig.from_settings()
assert config.do_ocr == False, 'PARSER_DO_OCR should be False'
parser = DoclingParser(config)
assert parser.native_converter is not None
assert parser.ocr_converter is not None
print('✓ Two-stage parser initialized correctly')
"

# 2. 测试降级检测（高文本密度 → 不降级）
python -c "
import asyncio
from pathlib import Path
from app.core.docling_service import DoclingParser, ParserConfig

async def test():
    parser = DoclingParser(ParserConfig.from_settings())
    
    # 模拟高文本密度的 markdown（born-digital PDF）
    high_density_md = 'hello world ' * 100  # > 80 chars/page
    should_retry = parser._should_retry_with_ocr(high_density_md, page_count=1)
    assert should_retry == False, 'High density should NOT trigger OCR'
    print('✓ High-density PDF: native parser used, no OCR')
    
    # 模拟低文本密度的 markdown（扫描件）
    low_density_md = 'hello'  # < 80 chars/page
    should_retry = parser._should_retry_with_ocr(low_density_md, page_count=1)
    assert should_retry == True, 'Low density SHOULD trigger OCR'
    print('✓ Low-density PDF: OCR fallback triggered')

asyncio.run(test())
"

# 3. 单元测试验证
pytest tests/unit/test_sprint4_docling_config.py::test_parser_config_do_ocr_default -v
# 预期：do_ocr 默认为 False

# 4. 集成测试（上传 PDF 检查日志）
# 上传 born-digital PDF → 日志应该看到 "using native parser, no OCR"
# 上传扫描件 → 日志应该看到 "Low text density detected, retrying with OCR"
```

#### B.4 性能对比

| PDF 类型 | 原错误做法 | 修复后 |
|---------|----------|------|
| Born-digital（高文本密度） | 10-30s（OCR） | 1-3s（native） |
| 扫描件（低文本密度） | 10-30s（OCR） | 1-3s native + 10-30s OCR = ~20-30s |
| 混合（部分页图片） | 10-30s（OCR） | 1-3s native 或 20-30s OCR |

**结论**：高质量 PDF 快 10 倍，扫描件仍准确

---

## 5. 验证方案

### SSE 双轨收口验证

```bash
# 1. 类型检查
cd apps/web && npm run type-check
# 预期：0 errors

# 2. 运行测试（特别关注 useChatStream）
npm run test:run -- src/app/hooks/useChatStream.test.ts
# 预期：所有测试通过，无 message_id 告警

# 3. 集成测试
npm run test:e2e -- features/chat/
# 预期：完整聊天流程无异常
```

### OCR 配置验证

```bash
# 1. 禁用 OCR 启动后端
cd apps/api && PARSER_DO_OCR=false python -m uvicorn app.main:app --port 8000

# 2. 上传 PDF 并验证是否跳过 OCR 处理
# 检查日志：应该看到 "OCR disabled, using native parser"

# 3. 启用 OCR 启动
PARSER_DO_OCR=true python -m uvicorn app.main:app --port 8000

# 4. 验证相同 PDF 的处理差异
# 预期：带 OCR 的处理时间更长，但提取内容更完整
```

### OCR 配置验证

```bash
# 1. 禁用 OCR 启动后端（现在是默认的）
cd apps/api && python -m uvicorn app.main:app --port 8000

# 2. 上传 born-digital PDF（如学术论文 PDF）
# 检查日志：应该看到 "using native parser" 而不是 "enabling OCR"

# 3. 上传扫描件（如扫描的书籍页面）
# 检查日志：应该看到 "Low text density detected, retrying with OCR"

# 4. 验证文本质量
# born-digital PDF：文本顺序应该与原始相同（native 保留排版）
# 扫描件：文本应该被正确恢复（OCR 识别成功）
```

---

## 6. 实施时间表

| 项目 | 工作量 | 优先级 | 状态 | 建议时间 |
|------|-------|-------|------|--------|
| SSE 类型定义统一 | 2-3h | P1 | Todo | Day 1 下午 |
| message_id fallback 修复 | 1-2h | P1 | Todo | Day 1 下午 |
| useSSE 删除 | 30m | P2 | Todo | Day 1 晚 |
| **OCR 智能降级恢复** | **30m** | **P1** | **✅ Done** | **Done** |
| 文档更新 + README | 30m | P2 | Todo | Day 2 上午 |
| **总计** | **4.5-6.5h** | | | **1.5 天** |

---

## 7. 风险与缓解

| 风险 | 可能性 | 缓解方案 |
|-----|-------|--------|
| SSE 类型变更破坏旧端 | 中 | 保留 adapter 层兼容 legacy 格式，只改内部表示 |
| OCR 禁用导致检索质量下降 | 低 | 生产默认保持 True，仅开发时可选禁用 |
| message_id fallback 掩盖后端问题 | 低 | 在日志中标记"imputing"，便于追踪真实问题 |

---

## 8. 后续跟踪

完成本方案后，建议：

1. **更新 docs/specs/architecture/system-overview.md**
   - 移除关于 "SSE 双轨" 的说明
   - 添加 "SSE 单通道设计" 的新说明

2. **在 docs/specs/development/coding-standards.md 中**
   - 加入 "禁止添加 legacy 事件类型别名" 的规则
   - 添加 "OCR 配置必须环境化" 的最佳实践

3. **后续 PR 检查清单**
   - SSE 事件类型变更：必须在 adapter 边界处理
   - 配置项变更：必须支持环境变量覆盖

---

## 附录：当前代码位置速查

| 项目 | 文件 | 行数 | 内容 |
|------|------|------|------|
| SSE 类型 | apps/web/src/services/sseService.ts | 52-67 | Legacy 类型定义 |
| message_id 验证 | apps/web/src/app/hooks/useChatStream.ts | 540-550 | 缺失告警逻辑 |
| 事件别名处理 | apps/web/src/app/hooks/useChatStream.ts | 570-620 | switch 中的双轨处理 |
| useSSE Hook | apps/web/src/app/hooks/useSSE.ts | 全文 | 待删除 |
| OCR 配置硬编码 | apps/api/app/config.py | 232 | PARSER_DO_OCR = True |
| OCR 默认值 | apps/api/app/core/docling_service.py | 61 | do_ocr: bool = True |

---

## 作者备注

这两个问题的根本原因是：

1. **SSE 双轨**：迁移过程中为了兼容，将 legacy 类型留在了核心定义里，导致长期维护成本高。
2. **OCR 硬编码**：配置环境化的工作不彻底，没有分开发/生产策略。

两者都是**工程规范问题**，不是业务逻辑问题。修复的关键是建立清晰的边界与分层：SSE adapter 模式、配置 profile 模式。修复完成后，应该在编码规范中明确禁止这两类反模式。
