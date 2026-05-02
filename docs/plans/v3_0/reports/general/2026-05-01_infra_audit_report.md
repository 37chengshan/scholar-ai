# ScholarAI 基础设施与配置审查报告

**审查日期:** 2026-05-01

---

## 审查概要

| 维度 | 问题数 | 严重 | 高 | 中 | 低 |
|------|--------|------|-----|-----|-----|
| Docker 配置 | 8 | 2 | 3 | 2 | 1 |
| 部署配置 | 7 | 3 | 2 | 1 | 1 |
| Nginx 配置 | 5 | 1 | 3 | 1 | 0 |
| 监控和可观测性 | 3 | 1 | 1 | 1 | 0 |
| CI/CD | 5 | 0 | 2 | 2 | 1 |
| 环境管理 | 6 | 4 | 1 | 1 | 0 |
| **合计** | **34** | **11** | **12** | **8** | **3** |

---

## 1. Docker 配置

### D-01 [严重] Dockerfile 未使用多阶段构建，镜像臃肿

**文件:** `apps/api/Dockerfile` (全文)

**问题:** 单阶段构建，包含 build-essential、gcc 等编译工具链在最终镜像中。Python 3.11-slim 基础镜像加上 PyTorch、transformers 等重型依赖，最终镜像可能超过 5GB。

**建议:** 使用多阶段构建，第一阶段安装编译依赖并构建 wheel，第二阶段仅安装运行时依赖。

---

### D-02 [严重] 容器以 root 用户运行

**文件:** `apps/api/Dockerfile` (全文)

**问题:** Dockerfile 中没有 `USER` 指令，uvicorn 以 root 身份运行。若容器被攻破，攻击者将获得宿主机 root 权限。

**建议:** 添加 `RUN useradd -m appuser` 和 `USER appuser`。

---

### D-03 [高] Dockerfile 缺少 HEALTHCHECK 指令

**文件:** `apps/api/Dockerfile`

**问题:** 健康检查仅在 docker-compose.yml 中定义，Dockerfile 本身没有 HEALTHCHECK。如果直接 `docker run` 该镜像，无法自动检测服务状态。

**建议:** 在 Dockerfile 中添加 `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`。

---

### D-04 [高] docker-compose.yml 中 redis 和 neo4j 缺少 healthcheck

**文件:** `docker-compose.yml` 第 23-30 行 (redis), 第 33-45 行 (neo4j)

**问题:** Redis 和 Neo4j 服务没有定义 healthcheck，但其他服务依赖它们 (`condition: service_started`)。`service_started` 仅表示容器已启动，不代表服务就绪。

**建议:** 为 Redis 添加 `redis-cli ping` 健康检查，为 Neo4j 添加 `cypher-shell` 健康检查，并将依赖条件改为 `service_healthy`。

---

### D-05 [高] docker-compose.yml 中 backend volumes 重复挂载 huggingface 缓存

**文件:** `docker-compose.yml` 第 163-164 行

**问题:** `~/.cache/huggingface:/root/.cache/huggingface:ro` 被挂载了两次。

**建议:** 移除重复的挂载行。

---

### D-06 [中] MinIO 使用硬编码默认凭据

**文件:** `docker-compose.yml` 第 74-75 行, `docker-compose.demo.yml` 第 65-66 行

**问题:** `MINIO_ACCESS_KEY: minioadmin` 和 `MINIO_SECRET_KEY: minioadmin` 使用 MinIO 默认凭据，未通过环境变量注入。

**建议:** 使用 `${MINIO_ACCESS_KEY:-minioadmin}` 模式，生产环境必须修改。

---

### D-07 [中] etcd 和 minio 镜像版本过旧

**文件:** `docker-compose.yml` 第 49 行 (etcd v3.5.5), 第 71 行 (minio RELEASE.2023-03-20)

**问题:** etcd v3.5.5 (2022年发布) 和 MinIO 2023年3月版本存在已知安全漏洞。

**建议:** 升级到最新的稳定版本。

---

### D-08 [低] docker-compose.yml 使用已废弃的 version 字段

**文件:** `docker-compose.yml` 第 1 行, `docker-compose.demo.yml` 第 1 行

**问题:** `version: '3.8'` 在 Docker Compose V2 中已被忽略。

**建议:** 移除 version 字段。

---

## 2. 部署配置

### P-01 [严重] 生产环境 JWT_SECRET 使用弱默认值

**文件:** `docker-compose.yml` 第 141 行

**问题:** `JWT_SECRET=${JWT_SECRET:-your-secret-key-change-in-production}` -- 如果环境变量未设置，将使用这个可预测的默认值。攻击者可直接伪造 JWT token。

**建议:** 启动时校验 JWT_SECRET 必须已设置且长度 >= 32 字符，否则拒绝启动。

---

### P-02 [严重] .env 文件中包含真实 API 密钥且在磁盘上明文存储

**文件:** `.env` 第 57 行

**内容:** `ZHIPU_API_KEY=0f6ec31f2d784bd49c9d5fad63bfad6a.Me0RBM1adkoOiQc9`

**问题:** 真实的智谱 API 密钥硬编码在 .env 文件中。虽然 .env 被 .gitignore 排除，但该密钥已暴露在本地磁盘。

**建议:** 立即轮换该 API 密钥，使用环境变量或密钥管理服务注入。

---

### P-03 [严重] apps/api/.env 包含多个真实密钥

**文件:** `apps/api/.env` 第 44 行、第 58 行

**内容:** `ZHIPU_API_KEY=0f6ec31f2d784bd49c9d5fad63bfad6a.Me0RBM1adkoOiQc9`, `SEMANTIC_SCHOLAR_API_KEY=M21X7cAEFkr6R6LwVkhz2MyZFmI0D0UX37gvNDj0`

**问题:** 真实 API 密钥明文存储。`apps/api/.env` 未被 .gitignore 排除（仅 `.env` 被排除，但 `apps/api/.env` 不在规则中）。

**建议:** 立即轮换密钥。将 `apps/api/.env` 添加到 .gitignore。

---

### P-04 [高] 部署脚本以 root 运行 systemd 服务

**文件:** `deploy-cloud.sh` 第 236 行

**问题:** `User=root` -- ScholarAI Worker 服务以 root 权限运行，违反最小权限原则。

**建议:** 创建专用的 `scholarai` 用户运行服务。

---

### P-05 [高] 部署脚本缺少回滚策略

**文件:** `deploy-cloud.sh`, `deploy-cloud-minimal.sh`, `deploy-cloud-fixed.sh`

**问题:** 三个部署脚本都没有版本管理、备份或回滚机制。部署失败后无法自动恢复。

**建议:** 实现蓝绿部署或滚动更新策略，添加数据库备份步骤和回滚脚本。

---

### P-06 [中] 三个部署脚本方案不一致

**文件:** `deploy-cloud.sh` (systemd 服务), `deploy-cloud-minimal.sh` (手动启动), `deploy-cloud-fixed.sh` (Python 3.6 兼容)

**问题:** 三种部署方式并存，版本固定的依赖不同，容易造成部署混乱。

**建议:** 统一为一种部署方案，使用 Docker 部署替代裸机部署。

---

### P-07 [低] deploy-cloud.sh 中 start-worker.sh 的 export $(cat .env | xargs) 不安全

**文件:** `deploy-cloud.sh` 第 213 行

**问题:** `export $(cat .env | xargs)` 无法正确处理包含空格或特殊字符的值，且会将所有变量导出到子进程。

**建议:** 使用 `source .env` 或 `python-dotenv` 加载。

---

## 3. Nginx 配置

### N-01 [严重] 缺少安全响应头

**文件:** `nginx/nginx.conf` (全文)

**问题:** 未配置任何安全头，包括:
- `X-Frame-Options` (防点击劫持)
- `X-Content-Type-Options: nosniff` (防 MIME 嗅探)
- `X-XSS-Protection`
- `Content-Security-Policy`
- `Strict-Transport-Security` (HSTS)
- `Referrer-Policy`

**建议:** 在 server 块中添加所有安全头。

---

### N-02 [高] 无 SSL/TLS 配置

**文件:** `nginx/nginx.conf` 第 44-143 行

**问题:** 仅监听 HTTP 80 端口，没有 HTTPS 配置。虽然 docker-compose.yml 中 nginx 服务暴露了 443 端口，但 nginx.conf 中没有 SSL 证书配置和 443 监听。

**建议:** 添加 SSL/TLS 配置，使用 TLS 1.2+，配置 HTTP 到 HTTPS 的重定向。

---

### N-03 [高] OpenAPI 文档端点公开暴露

**文件:** `nginx/nginx.conf` 第 120-133 行

**问题:** `/docs`、`/redoc`、`/openapi.json` 端点无认证保护，任何人可查看完整的 API 结构。

**建议:** 生产环境应禁用或通过 IP 白名单/mTLS 保护这些端点。

---

### N-04 [高] 通用 location / 未设置 client_max_body_size

**文件:** `nginx/nginx.conf` 第 136-142 行

**问题:** 只有 `/parse/` 路径设置了 `client_max_body_size 50M`，其他路径使用 nginx 默认值 1M。但如果其他 API 端点也需要上传文件，会被限制。

**建议:** 在 server 块级别设置合理的 `client_max_body_size`。

---

### N-05 [中] SSE 流式端点路径匹配不够精确

**文件:** `nginx/nginx.conf` 第 78-94 行

**问题:** `location /api/v1/chat` 使用前缀匹配，会匹配所有以 `/api/v1/chat` 开头的路径（如 `/api/v1/chat/sessions`），但这些子路径可能不需要 SSE 流式配置。

**建议:** 使用精确匹配 `location = /api/v1/chat/stream` 或正则匹配特定的流式端点。

---

## 4. 监控和可观测性

### O-01 [严重] 可观测性基础设施完全缺失

**文件:** `infra/observability/README.md`

**问题:** `infra/observability/` 目录仅有 README.md 占位文件，没有任何监控、告警或追踪配置。生产环境无法知道:
- 服务是否健康
- 请求延迟和错误率
- 资源使用情况
- 异常和错误

**建议:** 至少配置:
- Prometheus + Grafana 用于指标收集和可视化
- 结构化日志聚合 (ELK/Loki)
- 基础告警规则 (服务宕机、错误率飙升、高延迟)

---

### O-02 [高] 日志仅输出到 stdout/stderr，无持久化和轮转

**文件:** `docker-compose.yml` (所有服务), `deploy-cloud.sh` 第 243-244 行

**问题:** Docker 服务未配置日志驱动和大小限制。deploy-cloud.sh 中的日志直接 tee 到文件，无轮转机制，可能导致磁盘占满。

**建议:** 在 docker-compose.yml 中配置日志驱动:
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

---

### O-03 [中] Nginx 日志格式缺少关键字段

**文件:** `nginx/nginx.conf` 第 13-16 行

**问题:** 日志格式缺少 `$request_time`、`$upstream_response_time` 等性能指标字段，无法排查慢请求。

**建议:** 在 log_format 中添加请求耗时和上游响应时间。

---

## 5. CI/CD

### C-01 [高] Lint 检查设置了 continue-on-error

**文件:** `.github/workflows/test.yml` 第 199 行、第 205 行

**问题:** Ruff 和 Black 的 lint 步骤都设置了 `continue-on-error: true`，意味着代码质量问题不会阻止合并。

**建议:** 移除 `continue-on-error`，将 lint 错误作为硬性阻断条件。

---

### C-02 [高] 缺少容器镜像安全扫描

**文件:** `.github/workflows/` (所有 workflow)

**问题:** CI 流水线中没有使用 Trivy、Snyk 或其他工具对 Docker 镜像进行漏洞扫描。

**建议:** 在 build job 中添加镜像扫描步骤。

---

### C-03 [中] 缺少自动化部署流水线

**文件:** `.github/workflows/` (所有 workflow)

**问题:** 没有 CD (持续部署) 流水线。所有部署依赖手动执行 deploy-cloud.sh 脚本。

**建议:** 实现基于 GitHub Actions 的自动部署流程，至少覆盖 staging 环境。

---

### C-04 [中] test.yml 中测试覆盖率上报配置可能不生效

**文件:** `.github/workflows/test.yml` 第 173-181 行

**问题:** pytest 命令没有 `--cov` 参数生成 coverage.xml，但 Codecov 步骤尝试上传 `./apps/api/coverage.xml`。

**建议:** 在 pytest 命令中添加 `--cov=app --cov-report=xml:coverage.xml`。

---

### C-05 [低] Makefile 中 logs-api 和 logs-ai 指向不存在的服务名

**文件:** `Makefile` 第 63-64 行、第 66-67 行

**问题:** `logs-api` 引用 `docker-compose logs -f api`，`logs-ai` 引用 `docker-compose logs -f ai-service`，但 docker-compose.yml 中服务名是 `backend` 和 `celery_worker`。

**建议:** 更新 Makefile 中的服务名。

---

## 6. 环境管理

### E-01 [严重] .env.local 包含真实 API 密钥

**文件:** `.env.local` 第 57 行

**内容:** `ZHIPU_API_KEY=0f6ec31f2d784bd49c9d5fad63bfad6a.Me0RBM1adkoOiQc9`

**问题:** 与 .env 中相同的真实 API 密钥。虽然 .env.local 被 .gitignore 排除，但密钥已泄露。

**建议:** 立即轮换密钥。

---

### E-02 [严重] apps/api/.env.backup 被 git 跟踪且包含敏感信息

**文件:** `apps/api/.env.backup`

**问题:** git ls-files 显示 `apps/api/.env.backup` 被版本控制跟踪，可能包含历史凭据。

**建议:** 从 git 历史中移除 (`git rm --cached`)，添加到 .gitignore，轮换所有可能泄露的密钥。

---

### E-03 [严重] apps/api/.jwt_public.pem 被 git 跟踪

**文件:** `apps/api/.jwt_public.pem`

**问题:** JWT 公钥文件存在于 apps/api 目录。虽然公钥本身不是秘密，但如果这是与私钥配对的文件，需要确认私钥未被泄露。

**建议:** 确认私钥不在版本控制中，公钥文件移至配置目录。

---

### E-04 [严重] docker-compose.yml 中数据库密码使用弱默认值

**文件:** `docker-compose.yml` 第 10 行、第 37 行、第 131 行

**问题:** PostgreSQL 密码默认 `scholarai123`，Neo4j 密码默认 `scholarai123`。这些是可预测的弱密码。

**建议:** 移除默认值，要求通过环境变量显式设置。启动时校验密码强度。

---

### E-05 [高] 环境配置文件过多且存在冲突

**文件:** 根目录 `.env`, `.env.docker`, `.env.example`, `.env.local`, `.env.test`; `apps/api/.env`, `apps/api/.env.backup`, `apps/api/.env.example`

**问题:** 8 个环境配置文件，部分值不一致。例如:
- `.env` 第 75 行: `VITE_API_URL=http://localhost:4000` (指向已废弃的 Node.js 后端)
- `.env.local` 第 115 行: `VITE_API_URL=http://localhost:8000` (正确)
- `.env.docker` 第 145 行: `HF_HUB_OFFLINE=1` vs `.env.local` 第 125 行: `HF_HUB_OFFLINE=0`

**建议:** 统一环境配置策略，使用 `.env.example` 作为模板 + 按环境覆盖的分层方式。

---

### E-06 [中] .env.test 包含硬编码凭据且被 git 跟踪

**文件:** `.env.test` (全文)

**问题:** `JWT_SECRET=test-jwt-secret-for-e2e-tests` 和数据库密码 `scholarai123` 被提交到版本控制。虽然是测试环境，但建立了不良实践。

**建议:** 测试凭据应通过 CI 环境变量注入，不提交到代码库。

---

## 优先修复建议

### 立即行动 (P0 - 本周内)

1. **轮换所有已泄露的 API 密钥** -- `.env`、`.env.local`、`apps/api/.env` 中的 ZHIPU_API_KEY 和 SEMANTIC_SCHOLAR_API_KEY
2. **从 git 历史中清除 `apps/api/.env.backup`**
3. **将 `apps/api/.env` 添加到 .gitignore**
4. **为 JWT_SECRET 添加启动时校验**，拒绝弱默认值

### 短期行动 (P1 - 2 周内)

5. **Dockerfile 添加多阶段构建和非 root 用户**
6. **Nginx 添加安全头和 SSL/TLS 配置**
7. **为 redis/neo4j 添加 healthcheck**
8. **CI 中移除 lint 的 continue-on-error**

### 中期行动 (P2 - 1 个月内)

9. **搭建基础可观测性栈** (Prometheus + Grafana + 日志聚合)
10. **实现自动化部署流水线**
11. **统一环境配置管理**
12. **添加容器镜像安全扫描**

---

## 架构亮点 (做得好的部分)

- docker-compose.yml 中 postgres、milvus、etcd、minio 都有 healthcheck
- backend 和 celery_worker 有合理的资源限制 (memory: 4G)
- CI 有多层门禁: governance checks、type-check、unit tests、E2E tests、contract gate
- `scripts/check-runtime-hygiene.sh` 防止运行时产物被提交到 git
- 使用 `concurrency: cancel-in-progress: true` 避免 CI 资源浪费
- docker-compose.demo.yml 精简了不必要的服务 (neo4j, nginx)
