# 🎓 ScholarAI

ScholarAI 是一个面向学术阅读与知识管理流的全栈 AI 工程化应用仓库。本仓库旨在通过严格的工程化约束、清晰的代码边界和多 Agent 协同体系，建立并长期维护一套高稳定性的大模型驱动架构。

---

## 🎯 核心目标 (Purpose)

- **固化架构边界**：统一前端、后端、数据编排的实现路径，杜绝代码目录漂移和散乱的重复实现。
- **标准化契约**：通过前后端强类型 API 契约协议，连接 UI、后台服务、异步处理与自动化测试流程。
- **文档与代码同构**：保证规范文档、设计图、CI/CD 流水线与实际代码结构同步演进，拒绝“过时文档”。
- **持续化治理**：利用严格合规的目录结构控制与自动化脚本门禁，长效维持代码卫生与开发可维护性。

---

## 📂 项目边界规范 (Scope & Boundaries)

当前阶段，系统的全部真实业务代码**必须**仅存在于以下两天核心实现路径：

*   **`apps/web/`** —— 前端真实代码主线（基于现代 Web 技术栈）。
*   **`apps/api/`** —— 后端真实代码主线（基于 Python 技术栈）。

其余辅助模块严格遵循以下边界：
*   **`infra/`**：部署与基础设施配置（Docker 编排、Nginx 路由、运维脚本等）。
*   **`tools/`**：脚手架、构建打包逻辑与辅助开发工具。
*   **`packages/*`**：跨栈共享资产的预留模块（当下**不承接**任何真实业务代码）。

---

## 📖 真理之源 (Source of Truth)

本项目高度依赖“规范即代码”的哲学。修改核心逻辑前，必须查阅并对齐以下文档：

**架构与设计**
- 🏠 架构总览：`docs/specs/architecture/system-overview.md` | `architecture.md`
- 🔌 API 契约：`docs/specs/architecture/api-contract.md`
- 🎨 UI/UX 规范：`docs/specs/design/frontend/DESIGN_SYSTEM.md`
- 📦 资源域模型：`docs/specs/domain/resources.md`
- 🤖 Agent 地图：`AGENTS.md`

**研发与治理**
- 💻 开发规范：`docs/specs/development/coding-standards.md`
- 🧪 测试策略：`docs/specs/development/testing-strategy.md`
- 🔀 PR 工作流：`docs/specs/development/pr-process.md`
- 🛡️ 边界基线：`docs/specs/governance/code-boundary-baseline.md`
- 📊 KPI 规范：`docs/specs/governance/governance-kpi-spec.md`

---

## 🛑 开发红线 (Hard Rules)

1. **整洁根目录**：根目录仅保留系统级配置，严禁放置 `*.pid`, `cookies.txt`, 业务临时日志或测试废弃物。
2. **唯一文档入口**：所有新增文档严格按类别写入 `docs/specs/` (规范) 或 `docs/plans/` (流转/报告)。**禁止**新建并平铺 `doc/`, `tmp/`, `legacy/` 等散乱文件夹。
3. **无缝路径管控**：除 `apps/web` 和 `apps/api` 外，**禁止**开辟第三条业务应用实现路径。
4. **运行时产物隔离**：严禁将以下文件提交到 Git 仓库：
    * `logs/`, `test-results/`, `uploads/`
    * `apps/web/test-results/`, `apps/web/*.log`
    * `apps/api/venv/`, `apps/api/htmlcov*`, `**/__pycache__/`
5. **代码分层强制性**：
    * **Web**: 页面组件（UI）不允许直连 API，数据拉取与更新逻辑必须统一下沉至 `services` 或专属 `hooks`。
    * **API**: 路由层（Routers）禁止混入杂糅业务编排，必须作为 Controller 直接分发给 `service` 层处理。API 响应必须符合统一规范格式。

---

## 🔄 变更联动要求 (Required Updates)

当触发以下变动时，必须同步（且在一个 PR 内）完成文档的更新：
- 更改网络流转/架构组件 👉 更新 `system-overview.md` 和 `architecture.md`
- 更改/新增后端接口 👉 更新 `api-contract.md`
- 更改核心实体状态 👉 更新 `resources.md`
- 调整测试与质控策略 👉 更新治理基线及对应的 playbook / handbook 文件。

---

## 🚀 部署与验证 (Verification & Run)

**环境要求**
- Node.js 20+
- Python 3.11+
- Docker / Docker Compose

**本地快速启动**
\`\`\`bash
# 启动基础设施编排
make dev

# 启动 Backend (API)
cd apps/api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 启动 Frontend (Web)
cd apps/web && npm install
npm run dev
\`\`\`

**门禁与合规检测 (CI Commands)**
\`\`\`bash
# 1. 完整全链路验证 (默认包含集测)
bash scripts/verify/run-all.sh
# 或使用快捷指令: make verify / npm run verify:all

# 2. 快速本地验证 (显式跳过集成测试)
VERIFY_QUICK=1 bash scripts/verify/run-all.sh

# 3. 审查脚本与目录卫生
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
\`\`\`
