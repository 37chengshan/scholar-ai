# v3.4 Frontend Evidence UI + Pretext Report

## Scope

- Chat：Evidence-first 面板（claim/citation/evidence block/quality/fallback）接入主渲染链。
- Read：接入 source_id 导航、chunk 高亮提示与证据侧注。
- Search：新增 v3 分层 evidence 结果展示与 Read 跳转。
- Text Layout：引入 Pretext runtime，统一测量入口和缓存。

## Implemented Changes

- Chat 数据通路：`done` 事件扩展字段已落盘到 `message.answerContract`。
- MessageFeed：assistant 完整消息支持 EvidencePanel。
- Read 侧面板：当 URL 含 `source_id` 时展示 `SourceChunkHighlight` 和 `EvidenceSideNote`。
- Search 右侧分析区：新增 Layered Evidence 区块，展示 paper/section/evidence/relation 分层计数与前 3 条证据跳转按钮。
- Text layout runtime：补齐 LRU 与 pretext fallback 守护，避免 runtime 空对象导致测试失败。

## Verification

- `cd apps/web && npm run type-check`：passed
- `cd apps/web && npm run test:run -- src/features/chat/components/evidence/EvidencePanel.test.tsx src/lib/text-layout/__tests__/measure.test.ts src/lib/text-layout/__tests__/performance.test.ts`：3 passed
- 备注：Vitest 环境存在 jsdom canvas `getContext` not implemented 警告，不影响本次断言结果。

## Risk Notes

- Search 分层 evidence 当前按查询实时调用 `/api/v1/search/evidence`，后续可加 debounce 与请求取消减少抖动。
- Read 页面当前采用“提示 + 侧注”形态，若需 PDF 内部可视高亮，需要在 PDF 渲染层追加坐标映射。
