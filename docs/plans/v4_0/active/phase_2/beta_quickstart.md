---
owner: product-engineering
status: asset-ready
depends_on:
  - demo_dataset.md
  - demo_environment_policy.md
  - known_limitations.md
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-assets
---

# v4.0 Phase 2 Beta Quickstart

## 1. 目标

本 quickstart 用于 controlled beta 受控试用，不是 marketing demo。

完成一次 run 的标准不是“页面都打开了”，而是把真实 workflow、evidence probe、降级口径和反馈入口都走完。

## 2. 前提

1. 环境必须符合 `demo_environment_policy.md` 的 local controlled beta 策略。
2. 默认样本集使用 `beta-mainline-001`。
3. 本次 run 必须有唯一 `run_id`，并为 KB 使用 `scholarai-beta-<run_id>` 前缀。
4. 使用者必须先阅读 `known_limitations.md`，尤其是 Review `partial / insufficient_evidence` 与 AI 输出审查约束。
5. Chat handoff 当前是 `prefill-only`：进入 Chat 后必须人工确认并发送 prompt，这不是产品失败。

## 3. Happy Path

| step | action | expected timing | pass condition | degraded / blocked handling |
|---|---|---|---|---|
| 1 | 进入本地 ScholarAI，使用 demo 账号登录或记录有效本地身份 | 1-2 min | 可以进入 Dashboard/Search，且身份记录清晰 | 若身份不明或环境指向错误 backend，立即 `blocked` |
| 2 | 创建或确认新 KB：`scholarai-beta-<run_id>` | <1 min | KB 创建成功且为空 | 若命名空间已被旧 run 占用，重新 reset |
| 3 | Search `Attention Is All You Need` | 0.5-1 min | 返回目标论文并显示真实 import CTA | 若结果噪音高，改用 `1706.03762`；仍失败则 `blocked` |
| 4 | 把 D-001 导入刚创建的 KB | 3-5 min | import job 完成并显示论文已进入 KB | 若超时或失败，记录 job 状态并提交 feedback |
| 5 | 从 KB 打开 Read 页面 | <1 min | 论文正文与 AI summary panel 可读 | 若页面可开但内容缺失，标记 `partial` |
| 6 | 从 paper context 进入 Chat，确认预填 prompt 后人工发送，提问 Transformer 解决的核心问题 | 1-2 min | 返回带 citation/evidence 的回答，且操作者明确经历了 prefill-only 手动确认 | 若预填缺失、回答无证据或 jump 失败，标记 `partial` |
| 7 | 生成 Notes / paper summary | <1 min | Notes 非空并可被后续页面消费 | 若 Notes 空白或断链，标记 `partial` |
| 8 | Search `A Survey of Large Language Models` 并导入同一 KB | 3-5 min | 第二篇论文成功入库 | 若搜索不稳，改用 `2303.18223`；仍失败则本轮改为 `partial` |
| 9 | 在同一 KB 上运行 Compare | 1-2 min | Compare 区分原始 Transformer 论文与后续 survey 角色 | 若 Compare 缺失、串源或空白，标记 `partial` 或 `fail` |
| 10 | 运行 Review | 1-3 min | 记录 Review 是 `pass / partial / fail` | `partial / insufficient_evidence` 不是成功，必须转入 feedback |

## 4. 必做 Evidence Probe

1. Chat 或 Review 至少执行一次 citation jump，确认能回到论文内容。
2. Compare 必须区分 D-001 与 D-040，不得把两篇论文混成同一结论。
3. Review 若返回 `partial / insufficient_evidence`，必须把 omitted 部分记录进 feedback，而不是当作闭环成功。

## 5. Degraded Path

以下任一情况出现时，本轮 walkthrough 仍可继续，但结果只能记为 `partial`：

1. Search 可用，但 provider 延迟明显，必须依赖精确 arXiv ID 才能命中目标论文。
2. Import 成功，但首轮处理接近 4-5 分钟。
3. Read、Chat、Notes 可用，但 citation jump 不稳定。
4. Compare 或 Review 可执行，但结果带 `partial / insufficient_evidence`。

以下任一情况出现时，本轮必须记为 `blocked`：

1. demo 账号或 KB 命名空间无法证明 fresh-state。
2. import job 无法完成，或旧任务仍在污染当前 run。
3. frontend/backend 指向混乱，无法确认当前页面来自本地受控环境。

## 6. 恢复路径

| failure point | recovery |
|---|---|
| Search 结果不稳定 | 改用精确 arXiv ID；仍失败则停止扩展样本并提反馈 |
| Import 等待时间过长 | 记录 job id、等待时长和 worker 状态；不要提前宣称失败或成功 |
| Read 页面无内容 | 先确认 import 是否真正完成，再检查 KB 页面与 paper entry |
| Chat 进入后未自动发送 | 这是已知 `prefill-only` 行为；人工确认 prompt 后再发送，并把该行为记录为 limitation 而非故障 |
| Chat 无 citation | 记录 prompt、回答与 evidence 缺口，转入 feedback |
| Compare/Review 部分空白 | 归类为 `partial`，把缺失 section 与 `insufficient_evidence` 写入 feedback |

## 7. 不支持项

1. 不支持 public beta、自助注册或无人陪跑。
2. 不支持把 Review `partial` 写成完成。
3. 不支持在 staging/cloud 上直接复制本 quickstart 作为放行依据。
4. 不支持把 AI 输出当成无需 citation 审查的事实陈述。
5. 不支持把 Chat handoff 需要人工发送误判成自动断链故障。

## 8. 结束动作

1. 把本次 `run_id`、dataset_id、KB 名称、主要 evidence probe 结果写入 walkthrough 记录。
2. 对所有 `partial / fail / blocked` 项填写 `feedback_triage_template.md`。
3. 如果本轮没有 fresh-state 证明，不得写 `demo-ready` 或 `controlled-beta-ready`。