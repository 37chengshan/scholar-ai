# Benchmarks

## 目标

建立 Chat、Search/KB、RAG、Performance 四类可回归基线。

## 套件

- chat_stability
- search_workflow
- import_workflow
- rag_quality
- performance_baseline

## 运行

```bash
bash scripts/run-benchmarks.sh
python scripts/check-benchmark-thresholds.py
```

## 产物位置

- apps/api/artifacts/benchmarks/*.json
- apps/api/artifacts/benchmarks/*.md

## 阈值管理

阈值定义在 apps/api/tests/benchmarks/thresholds.py。

更新阈值前请在 PR 中附上基线报告对比。
