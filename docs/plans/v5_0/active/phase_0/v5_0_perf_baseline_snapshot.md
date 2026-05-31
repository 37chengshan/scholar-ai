---
owner: product-engineering
status: baseline-frozen
last_verified_at: 2026-05-31
measurement_method: static analysis + dependency inspection (no live build run)
scope:
  - apps/web (frontend bundle, source code, dependencies)
  - apps/api (python source, tests)
  - vite.config.ts (build configuration)
---

# v5.0 Phase 5.0-0 Performance Baseline Snapshot

> 本文是 v5.0 开始任何性能优化前的**真实测量基线**。所有后续 phase 的优化必须能在 5.0-9 release gate 时跑出"显著优于本 baseline"的数字,否则不允许写 release-pass。
>
> 本 baseline 是 phase_0 的 deliverable,不是最终测量。phase 5.0-2 完成后会跑一份完整 Lighthouse CI baseline,phase 5.0-9 会跑 release gate 最终测量。

## 1. 测量方法与限制

本次 baseline 用**静态测量**(目录体积、依赖体积、配置审查、代码行数)产出,**未跑 production build,未跑 Lighthouse**,原因:

1. Phase 5.0-2 才正式接入 Lighthouse CI 与 visualizer
2. 当前 Vite 配置无 manualChunks,跑 build 也无法得到 phase 5.0-2 之后的可比数据
3. 现有 `apps/web/dist/` 是 May 6 的旧产物,不能用作真相

phase 5.0-2 完成后必须重做一次"动态 baseline" (build + Lighthouse + Web Vitals 实测) 并归档到 `docs/plans/v5_0/reports/`。

## 2. 前端代码与依赖体积 (apps/web)

### 2.1 源码体积

```
src 总大小:          3.2 MB
```

| feature 目录 | 大小 | 文件数 (非 test) | 备注 |
|---|---|---|---|
| `features/chat` | **536 KB** | 59 | 全主链最重,Phase 5.0-6 精修 |
| `features/kb` | 196 KB | 19 | Phase 5.0-1/5.0-2 适配 token |
| `features/workflow` | 124 KB | (跨 phase) | dashboard 用 |
| `features/search` | 116 KB | 13 | Phase 5.0-1 适配 |
| `features/notes` | 116 KB | 11 | Phase 5.0-5 深度重构 |
| `features/read` | 76 KB | 11 | Phase 5.0-4 + pretext |
| `features/uploads` | 64 KB | 8 | Phase 5.0-3 接路由 |
| `features/compare` | 56 KB | 5 | Phase 5.0-6 顺带打磨 |
| `features/settings` | 44 KB | — | 维护 |

**观察**:Chat 占源码 17%,与"工作量评估"一致;Read/Notes/Compare 体积小但**测试覆盖更差**,优化空间大。

### 2.2 依赖体积 (node_modules 实际占用)

| 依赖 | 体积 | 计划 |
|---|---|---|
| `pdfjs-dist` | **36 MB** | Phase 5.0-2 必须 dynamic import 隔到 Read 页 |
| `@tiptap/*` | 6.9 MB | Phase 5.0-2 按需加载 extensions,隔到 Notes 页 |
| `@radix-ui/*` | 3.9 MB | Phase 5.0-2 manualChunks 拆为 `vendor-radix` |
| `motion` | 484 KB | 单独 chunk |
| `react-pdf` | 588 KB | 与 pdfjs-dist 同 chunk |

**总 packages**: 87 dependencies + 17 devDependencies = 104

**观察**:`pdfjs-dist` 36 MB 是 raw npm 体积,gzipped chunk 估计 ~200KB。**没隔出 Read 页时它会进首屏**,这是当前最大性能风险点。

### 2.3 路由切分现状

- `apps/web/src/app/routes.tsx`: 152 行
- `React.lazy()` 包裹的 route:**8 个** (Dashboard, KB list, KB detail, Search, Read, Settings, Notes, Analytics, Compare)
- 缺失的优化:
  - ❌ 无 `manualChunks` 自定义分包
  - ❌ 无 `rollup-plugin-visualizer`
  - ❌ 无 `chunkSizeWarningLimit`
  - ❌ 无路由 preload (mouseover / visibility)
  - ❌ 无 font preload (Google Fonts 通过 `@import` 加载,阻塞首屏)

### 2.4 Vite 配置审查

`apps/web/vite.config.ts` 当前只有:
- `react()` + `tailwindcss()` 两个 plugin
- alias (`@`, `@scholar-ai/types`, `@scholar-ai/sdk`)
- dev 期间 `/api` proxy 到 8000
- `assetsInclude` (svg, csv)

**完全没有 build 期性能优化配置**。Phase 5.0-2 是从零建立。

## 3. 后端代码与测试 baseline (apps/api)

| 项 | 当前值 |
|---|---|
| `apps/api/app` 总大小 | **15 MB** (含 \_\_pycache\_\_) |
| `app/api` | 3.1 MB |
| `app/services` | 2.3 MB |
| `app/rag_v3` | 1.0 MB |
| `app/core` | 4.7 MB |
| pytest 测试文件 | **237** |
| vitest 测试文件 | 94 |
| Playwright E2E spec | **14** |

**观察**:
1. 后端 test 覆盖度 (237 files) 远高于前端 (94),与 v4.5 multidimensional audit 一致
2. Read 页 0 个 vitest, Compare 页 0 个 vitest — phase 5.0-4 / 5.0-6 必须补
3. E2E 14 个 spec 覆盖了 chat/kb/search/notes/compare/user-journey,但 Read 与 Upload 零覆盖

## 4. Core Web Vitals baseline (估计,不是实测)

phase 5.0-0 不跑 Lighthouse,但根据当前配置可以**预测**:

| 指标 | 预测值 | v5.0 目标 |
|---|---|---|
| LCP (Landing) | **> 3.0 s** (Google Fonts `@import` 阻塞) | < 2.5 s |
| LCP (Chat) | **> 3.5 s** (无 manualChunks, Chat feature 536KB 一次性进入) | < 2.5 s |
| LCP (Read) | **> 4.5 s** (pdfjs-dist 与 react-pdf 进入首屏路径) | < 2.5 s |
| INP (Chat SSE) | **> 250 ms** (无 virtualization, 长消息列表全量 DOM) | < 200 ms |
| CLS (Chat SSE) | **0.1 ~ 0.3** (流式期间 layout shift, P1-FE-001 已部分修但 message 高度未预测) | < 0.05 |
| FCP | > 2.0 s | < 1.5 s |
| TBT | > 300 ms | < 200 ms |

**phase 5.0-2 必须做一次真实 Lighthouse 测量验证以上预测,任何严重偏离必须立刻调整 5.0-2 / 5.0-4 / 5.0-6 的优化重点**。

## 5. Bundle Budget 当前差距 (静态推断)

按 phase 5.0-2 计划的 budget:

| 包 | budget (gz) | 当前估计 (gz) | 差距 |
|---|---|---|---|
| 首屏 entry | ≤ 80 KB | **未知 (需测)** | ? |
| 首屏 + 4 主路由 | ≤ 500 KB | **可能严重超** (pdfjs/tiptap 没隔) | 高风险 |
| `vendor-pdf` (Read 才需) | ≤ 200 KB | **进入首屏** | 高风险 |
| `vendor-tiptap` (Notes 才需) | ≤ 80 KB | **进入首屏** | 高风险 |
| 单 feature chunk | ≤ 80 KB | Chat 536KB raw / ~150KB gz 估 | 需拆 |

phase 5.0-2 的第一个 deliverable 必须是 **"接入 visualizer 跑出真实 chunk 分布"**,然后根据真实数据调整 manualChunks。

## 6. 治理类 baseline

| 项 | 当前 |
|---|---|
| `scripts/check-doc-governance.sh` | ✅ 存在 |
| `scripts/check-plan-governance.sh` | ✅ 存在 |
| `scripts/check-phase-tracking.sh` | ✅ 存在 |
| `scripts/check-governance.sh` | ✅ 存在 |
| `scripts/check-runtime-hygiene.sh` | ✅ 存在 |
| `scripts/check-structure-boundaries.sh` | ✅ 存在 |
| `scripts/check-code-boundaries.sh` | ✅ 存在 |
| `scripts/check-branch-lifecycle.sh` | ✅ 存在 |
| `scripts/check-contract-gate.sh` | ✅ 存在 |
| `scripts/check-pr-template-body.sh` | ✅ 存在 |
| `scripts/evals/run_v4_phase7_gate.py` | ✅ 存在 (待升级为 v5_release_gate) |
| Lighthouse CI 集成 | ❌ 缺失 |
| Bundle visualizer 集成 | ❌ 缺失 |

## 7. 不在本 baseline 范围

1. ❌ Live Lighthouse 测量 (5.0-2 deliverable)
2. ❌ Real user metrics (RUM) 数据 (无 RUM 接入)
3. ❌ 后端 latency p50/p95 全链路测量 (5.0-7 deliverable)
4. ❌ 移动端 perf baseline (v5.0 不做移动端)
5. ❌ Network throttling 下的测量 (5.0-9 release gate 含)

## 8. 5.0-9 release-pass 必须达到 (从 overview 第 8 节复制)

| 项 | 目标 |
|---|---|
| Lighthouse 主路由 (`/`, `/kb`, `/read`, `/chat`) | ≥ 90 |
| Bundle 首屏 (entry + critical CSS + 主路由 chunk) | ≤ 500 KB gz |
| LCP | < 2.5 s |
| INP | < 200 ms |
| CLS (含 SSE 期间) | < 0.05 |
| FCP | < 1.5 s |
| TBT | < 200 ms |

## 9. baseline 复测要求

下列动作触发本 baseline 自动失效,必须重新跑:

1. `apps/web/vite.config.ts` 出现 `manualChunks` 或 `rollupOptions` 改动
2. 引入新的大依赖 (>500KB raw)
3. 任何 phase closeout 后,5.0-2 必须重测一次
4. 5.0-9 release gate 必须包含一次完整 baseline 复测对比

## 10. 关键风险一句话

> 当前 Vite 配置零优化 + pdfjs-dist 进入首屏 + 无 virtualization + Google Fonts @import 阻塞,**预计未做优化前任何路由 Lighthouse 分数都不会超过 70**。phase 5.0-2 必须把这条曲线整体抬起来,不然 5.0-4/5.0-5/5.0-6 的视觉优化只会增加体积。
