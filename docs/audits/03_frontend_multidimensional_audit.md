# 03 Frontend Multidimensional Audit (Phase0)

## 1. Audit Scope

- 范围: apps/web chat 主链路、auth helper、E2E 契约套件、responsive 断言。
- 目标: 确认 release gate 相关 P0/P1 在真实运行下稳定。

## 2. Verification Results

### 2.1 Type Safety

- 命令: pnpm type-check
- 结果: PASS

### 2.2 E2E Critical Suite

- 命令:
  - pnpm playwright test e2e/chat-critical.spec.ts --reporter=line
  - pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line
  - pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line
  - pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line
- 结果:
  - chat-critical: 3 passed
  - chat-evidence: 1 passed
  - notes-rendering: 1 passed
  - chat-responsive: 1 passed

## 3. Issues Found and Fixed During Phase0

### 3.1 Auth Submit Flakiness

- 现象: 登录按钮点击在动画/重渲染下偶发 detached/unstable。
- 修复: auth helper 增加稳定点击与 Enter 回退策略。
- 文件: apps/web/e2e/helpers/auth.ts

### 3.2 Runtime Import Crash

- 现象: /chat 页面出现 Unexpected Application Error，报错 pretext default export 不存在。
- 根因: @chenglou/pretext 以 default import 引入，运行时包不提供 default。
- 修复: 改为 namespace import。
- 文件: apps/web/src/lib/text-layout/measure.ts

### 3.3 E2E Selector Ambiguity

- 现象: chat-critical 中“对话/Chat”匹配 3 个链接，触发 strict mode violation。
- 修复: 使用唯一导航 selector（a[href="/chat"][title]）。
- 文件: apps/web/e2e/chat-critical.spec.ts

## 4. Release Gate Mapping

- C new chat session race: 通过
- D notes rendering: 通过
- E chat responsive layout/composer boundary: 通过
- G e2e contract update: 通过

## 5. Frontend Audit Verdict

- 结论: PASS（Phase0 范围内前端 gate 满足）。
