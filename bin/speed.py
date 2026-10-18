#!/usr/bin/env python3
"""Endpoint speed benchmark: TTFT / TPOT / output tok-s / total wall.

Pure stdlib; talks to any OpenAI-compatible /chat/completions endpoint
(vLLM, sglang, ollama, opencode/OpenRouter-style gateways, ...).

Usage:
  python3 bin/speed.py --base-url http://localhost:8000/v1 --model my-model --runs 5
  python3 bin/speed.py --base-url ... --model m --max-tokens 512 --no-stream
Env fallbacks: OPENAI_BASE_URL, OPENAI_API_KEY (or BENCH_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
import urllib.error
import urllib.request

PROMPTS = [
    "Explain in two sentences why the sky appears blue.",
    "Write a Python function that reverses a linked list, with a short docstring.",
    "Summarize the tradeoffs between INT8 and 4-bit weight quantization for LLM inference "
    "in five bullet points.",
]


def stream_once(base_url, api_key, model, prompt, max_tokens):
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    t0 = time.time()
    ttft = None
    chunks = 0
    usage = {}
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            choices = obj.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if delta.get("content") or delta.get("reasoning_content"):
                    if ttft is None:
                        ttft = time.time() - t0
                    chunks += 1
    total = time.time() - t0
    out_tokens = usage.get("completion_tokens") or chunks
    decode_s = max(total - (ttft or 0.0), 1e-6)
    return {
        "ttft_s": ttft,
        "total_s": total,
        "out_tokens": out_tokens,
        "out_tps": (out_tokens / decode_s) if out_tokens else None,
        "prompt_tokens": usage.get("prompt_tokens"),
    }


def nonstream_once(base_url, api_key, model, prompt, max_tokens):
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        obj = json.loads(r.read().decode())
    total = time.time() - t0
    usage = obj.get("usage", {})
    out_tokens = usage.get("completion_tokens") or 0
    return {
        "ttft_s": None,
        "total_s": total,
        "out_tokens": out_tokens,
        "out_tps": (out_tokens / total) if out_tokens and total else None,
        "prompt_tokens": usage.get("prompt_tokens"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1"))
    ap.add_argument("--api-key", default=os.environ.get("BENCH_API_KEY") or os.environ.get("OPENAI_API_KEY", "EMPTY"))
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=3, help="runs per prompt")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--no-stream", action="store_true")
    ap.add_argument("--out", default=None, help="append JSONL results here")
    a = ap.parse_args()

    fn = nonstream_once if a.no_stream else stream_once
    rows = []
    for pi, prompt in enumerate(PROMPTS):
        for k in range(a.runs):
            try:
                r = fn(a.base_url, a.api_key, a.model, prompt, a.max_tokens)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                print(f"❌ run p{pi+1}#{k+1} failed: {e}")
                continue
            r.update({"prompt_idx": pi + 1, "run": k + 1, "model": a.model, "base_url": a.base_url})
            rows.append(r)
            print(
                f"  p{pi+1}#{k+1}: ttft={r['ttft_s'] and round(r['ttft_s'],3)}s "
                f"total={r['total_s']:.2f}s out_tok={r['out_tokens']} "
                f"out_tps={r['out_tps'] and round(r['out_tps'],1)}"
            )

    if not rows:
        print("no successful runs")
        return 1

    def m(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return st.mean(vals) if vals else None

    def p50(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return st.median(vals) if vals else None

    print()
    print(f"== speed: {a.model} @ {a.base_url} (n={len(rows)}) ==")
    print(f"  TTFT      mean {m('ttft_s') and round(m('ttft_s'),3)}s | p50 {p50('ttft_s') and round(p50('ttft_s'),3)}s")
    print(f"  total     mean {m('total_s') and round(m('total_s'),2)}s | p50 {p50('total_s') and round(p50('total_s'),2)}s")
    print(f"  out tok/s mean {m('out_tps') and round(m('out_tps'),1)} | p50 {p50('out_tps') and round(p50('out_tps'),1)}")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"  results appended -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
