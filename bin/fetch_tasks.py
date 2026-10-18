#!/usr/bin/env python3
"""Fetch the vendored low/mid tier tasks from the openbench repo (MIT license).

Layout produced:
  tasks/low/<task>/      <- openbench core tasks (self-contained mini repos)
  tasks/mid/<task>/      <- openbench imported Terminal-Bench tier (upstream Apache-2.0)

Each task dir keeps the openbench layout: instruction.md, workspace/, checker.sh,
checker_data/, optional solution/, PROVENANCE.md.

Usage: python3 bin/fetch_tasks.py [--repo owner/name] [--ref main]
"""
import argparse
import json
import os
import sys
import urllib.request

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

LOW = ["make-ci-green", "add-feature", "misleading-error"]
MID = [
    "db-wal-recovery",
    "raman-fitting",
    "llm-inference-batching-scheduler",
]


def get(url: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "agent-benchmark", "Accept": accept}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="minghinmatthewlam/openbench")
    ap.add_argument("--ref", default="main")
    ap.add_argument(
        "--root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    a = ap.parse_args()

    tree = json.loads(get(f"{API}/repos/{a.repo}/git/trees/{a.ref}?recursive=1"))
    blobs = [f["path"] for f in tree["tree"] if f["type"] == "blob"]

    plans = [(t, f"tasks/{t}", "low") for t in LOW]
    plans += [(t, f"tasks-imported/terminal-bench/{t}", "mid") for t in MID]

    new = 0
    for task, prefix, tier in plans:
        files = [p for p in blobs if p.startswith(prefix + "/")]
        if not files:
            print(f"[{tier}] {task}: NO FILES (bad prefix {prefix})", file=sys.stderr)
            return 1
        for p in files:
            rel = p[len(prefix) + 1 :]
            dst = os.path.join(a.root, "tasks", tier, task, rel)
            if os.path.exists(dst):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(get(f"{RAW}/{a.repo}/{a.ref}/{p}"))
            new += 1
        print(f"[{tier}] {task}: {len(files)} files")
    print(f"done: {new} new files ({len(plans)} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
