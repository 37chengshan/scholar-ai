#!/usr/bin/env python3
"""Download arXiv papers for benchmark."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

PAPER_LIST = [
    {"arxiv_id": "1706.03762", "title": "Attention Is All You Need (Transformer)", "paper_id": "v2-p-001"},
    {"arxiv_id": "1810.04805", "title": "BERT", "paper_id": "v2-p-002"},
    {"arxiv_id": "1901.04592", "title": "GPT-2", "paper_id": "v2-p-003"},
    {"arxiv_id": "2005.14165", "title": "GPT-3", "paper_id": "v2-p-004"},
    {"arxiv_id": "2102.09690", "title": "Scaling Laws", "paper_id": "v2-p-005"},
    {"arxiv_id": "2201.11903", "title": "Chain of Thought", "paper_id": "v2-p-006"},
    {"arxiv_id": "2203.08165", "title": "Self-Consistency", "paper_id": "v2-p-007"},
    {"arxiv_id": "2210.03620", "title": "Tree of Thoughts", "paper_id": "v2-p-008"},
    {"arxiv_id": "2210.01611", "title": "ReAct", "paper_id": "v2-p-009"},
    {"arxiv_id": "2302.05296", "title": "Toolformer", "paper_id": "v2-p-010"},
    {"arxiv_id": "2112.04426", "title": "RETRO", "paper_id": "v2-p-011"},
    {"arxiv_id": "2204.00456", "title": "In-context Learning", "paper_id": "v2-p-012"},
    {"arxiv_id": "2005.00728", "title": "RAG", "paper_id": "v2-p-013"},
    {"arxiv_id": "2206.07658", "title": "FLAN", "paper_id": "v2-p-014"},
    {"arxiv_id": "2210.01077", "title": "T0", "paper_id": "v2-p-015"},
    {"arxiv_id": "2111.00342", "title": "Prompt Engineering", "paper_id": "v2-p-016"},
    {"arxiv_id": "2306.12547", "title": "Lora", "paper_id": "v2-p-017"},
    {"arxiv_id": "2308.12950", "title": "QLoRA", "paper_id": "v2-p-018"},
    {"arxiv_id": "2103.00001", "title": "Foundation Models", "paper_id": "v2-p-019"},
    {"arxiv_id": "2302.01378", "title": "SIFT", "paper_id": "v2-p-020"},
    {"arxiv_id": "2308.04240", "title": "Mixed Attention", "paper_id": "v2-p-021"},
    {"arxiv_id": "2304.13771", "title": "Long Context", "paper_id": "v2-p-022"},
    {"arxiv_id": "2303.17564", "title": "Flash Attention", "paper_id": "v2-p-023"},
    {"arxiv_id": "2308.10868", "title": "SMC", "paper_id": "v2-p-024"},
    {"arxiv_id": "2308.07093", "title": "Multi-Query", "paper_id": "v2-p-025"},
    {"arxiv_id": "2208.04591", "title": "Quantization", "paper_id": "v2-p-026"},
    {"arxiv_id": "2211.08891", "title": "Speculative Decoding", "paper_id": "v2-p-027"},
    {"arxiv_id": "2307.03195", "title": "H3", "paper_id": "v2-p-028"},
    {"arxiv_id": "2308.04656", "title": "Stark", "paper_id": "v2-p-029"},
    {"arxiv_id": "2310.15122", "title": "State Space Models", "paper_id": "v2-p-030"},
    {"arxiv_id": "2304.08485", "title": "Mamba", "paper_id": "v2-p-031"},
    {"arxiv_id": "2303.01391", "title": "Ring Attention", "paper_id": "v2-p-032"},
    {"arxiv_id": "2301.07067", "title": "Streaming LLMs", "paper_id": "v2-p-033"},
    {"arxiv_id": "2309.17453", "title": "Mixtral", "paper_id": "v2-p-034"},
    {"arxiv_id": "2310.08194", "title": "DeepSeek", "paper_id": "v2-p-035"},
    {"arxiv_id": "2310.06828", "title": "Small LMs", "paper_id": "v2-p-036"},
    {"arxiv_id": "2205.00445", "title": "Distillation", "paper_id": "v2-p-037"},
    {"arxiv_id": "2211.09345", "title": "Pruning", "paper_id": "v2-p-038"},
    {"arxiv_id": "2301.02758", "title": "Weight Tying", "paper_id": "v2-p-039"},
    {"arxiv_id": "2107.01330", "title": "PaLM", "paper_id": "v2-p-040"},
    {"arxiv_id": "2112.01996", "title": "GLM", "paper_id": "v2-p-041"},
    {"arxiv_id": "2303.18208", "title": "Qwen", "paper_id": "v2-p-042"},
    {"arxiv_id": "2209.02726", "title": "LLaMA", "paper_id": "v2-p-043"},
    {"arxiv_id": "2304.13734", "title": "Alpaca", "paper_id": "v2-p-044"},
    {"arxiv_id": "2304.10592", "title": "Vicuna", "paper_id": "v2-p-045"},
    {"arxiv_id": "2306.05685", "title": "WizardLM", "paper_id": "v2-p-046"},
    {"arxiv_id": "2304.12182", "title": "Self-Instruct", "paper_id": "v2-p-047"},
    {"arxiv_id": "2305.11201", "title": "UltraChat", "paper_id": "v2-p-048"},
    {"arxiv_id": "2305.14233", "title": "Orca", "paper_id": "v2-p-049"},
    {"arxiv_id": "2305.17993", "title": "LLaMA-2", "paper_id": "v2-p-050"},
]

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "evals" / "fixtures" / "benchmark_papers"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_arxiv_pdf(arxiv_id: str, output_path: Path) -> bool:
    """Download PDF from arXiv."""
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Failed to download {arxiv_id}: {e}")
        return False


def main() -> int:
    print(f"Downloading {len(PAPER_LIST)} papers to {OUTPUT_DIR}")
    success = 0
    failed = []
    
    for paper in PAPER_LIST:
        arxiv_id = paper["arxiv_id"]
        paper_id = paper["paper_id"]
        output_file = OUTPUT_DIR / f"{arxiv_id}.pdf"
        
        if output_file.exists():
            print(f"✓ {arxiv_id} already exists")
            success += 1
            continue
        
        print(f"Downloading {arxiv_id} ({paper_id})...")
        if download_arxiv_pdf(arxiv_id, output_file):
            success += 1
            print(f"✓ Downloaded {arxiv_id}")
        else:
            failed.append(arxiv_id)
    
    print(f"\n=== Results ===")
    print(f"Success: {success}/{len(PAPER_LIST)}")
    if failed:
        print(f"Failed: {failed}")
    
    manifest = {
        "total": len(PAPER_LIST),
        "success": success,
        "failed": len(failed),
        "papers": PAPER_LIST,
    }
    
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Manifest: {manifest_path}")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())