#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR/apps/api"
python -m tests.benchmarks.run_chat_benchmark
python -m tests.benchmarks.run_search_benchmark
python -m tests.benchmarks.run_import_benchmark
python -m tests.benchmarks.run_rag_benchmark
python -m tests.benchmarks.run_perf_baseline

cd "$ROOT_DIR/apps/web"
npm run test:run -- src/features/chat/__tests__/chatStability.benchmark.test.ts
npm run test:run -- src/features/search/__tests__/searchFlow.benchmark.test.ts
npm run test:run -- src/features/kb/__tests__/importFlow.benchmark.test.ts

echo "benchmark suite finished"
