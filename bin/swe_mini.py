#!/usr/bin/env python3
"""High tier: SWE-bench Verified mini (50 real GitHub issues, django+sphinx only).

Subcommands:
  fetch [--n 5]                 download the dataset via the HF datasets-server API
                                (stdlib only, no pyarrow) -> data/swe-mini/instances.jsonl
  list                          show cached instances
  run   --harness opencode --model M [--ids a,b] [--n 5] [--timeout-min 30]
                                clone repo at base_commit (git worktree), let the agent
                                edit it, capture `git diff` -> SWE-bench predictions JSONL
  eval  [--preds path] [--max-workers 2]
                                run the OFFICIAL SWE-bench harness (needs `pip install
                                swebench` + docker). Ingest resolved flags into
                                results/high-eval.jsonl for bin/report.py

Notes:
  * The agent edits "blind" (no repo env installed) — grading happens inside the official
    SWE-bench docker images, so pass/fail is independent of the local env.
  * Disk: repos ~0.3-1 GB (blob-filtered clones); docker images ~1-3 GB per instance.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "swe-mini")
WORK = os.path.join(ROOT, "work", "swe-mini")
RESULTS = os.path.join(ROOT, "results")
DS = "MariusHobbhahn/swe-bench-verified-mini"
ROWS_API = (
    "https://datasets-server.huggingface.co/rows"
    f"?dataset={DS}&config=default&split=test&offset={{off}}&length=100"
)
INSTANCES = os.path.join(DATA, "instances.jsonl")


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "agent-benchmark"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


# --------------------------------------------------------------------------- fetch
def cmd_fetch(a) -> int:
    os.makedirs(DATA, exist_ok=True)
    rows = http_json(ROWS_API.format(off=0))
    total = rows.get("num_rows_total", 0)
    all_rows = list(rows.get("rows", []))
    off = 100
    while len(all_rows) < total and off < 1000:
        more = http_json(ROWS_API.format(off=off))
        got = more.get("rows", [])
        if not got:
            break
        all_rows += got
        off += 100
    with open(INSTANCES, "w") as f:
        for r in all_rows:
            rec = r["row"]
            f.write(json.dumps(rec) + "\n")
    print(f"fetched {len(all_rows)} instances -> {INSTANCES}")

    # default subset: evenly spaced, respects per-repo balance
    n = a.n
    step = max(len(all_rows) // n, 1) if n else 1
    sel = all_rows[::step][:n]
    sel_path = os.path.join(DATA, f"subset-{n}.jsonl")
    with open(sel_path, "w") as f:
        for r in sel:
            f.write(json.dumps(r["row"]) + "\n")
    print(f"default subset ({len(sel)}) -> {sel_path}")
    for r in sel:
        row = r["row"]
        print(f"  {row['instance_id']}  ({row['repo']})")
    return 0


def load_instances() -> list[dict]:
    """Prefer the refreshed download in data/, fall back to the committed snapshot."""
    if os.path.exists(INSTANCES):
        path = INSTANCES
    else:
        path = os.path.join(ROOT, "tasks", "high", "instances.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path} — run: bash bench.sh high fetch")
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def cmd_list(a) -> int:
    rows = load_instances()
    for r in rows:
        print(f"{r['instance_id']}\t{r['repo']}\t{r['version']}")
    print(f"total: {len(rows)}")
    return 0


# --------------------------------------------------------------------------- run
def ensure_repo(repo: str) -> str:
    d = os.path.join(DATA, "repos", repo.replace("/", "__"))
    if not os.path.isdir(os.path.join(d, ".git")):
        os.makedirs(os.path.dirname(d), exist_ok=True)
        print(f"cloning {repo} (blob-filtered) -> {d}")
        subprocess.run(
            ["git", "clone", "--filter=blob:none", f"https://github.com/{repo}.git", d],
            check=True,
        )
    return d


def resolve_harness(hcfg: dict, model: str, workdir: str, prompt: str) -> list[str]:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import runner as R  # reuse harness resolution

    return R.harness_cmd(hcfg, model, workdir, prompt)


def cmd_run(a) -> int:
    harnesses = json.load(open(os.path.join(ROOT, "config", "harnesses.json")))
    hcfg = harnesses.get(a.harness)
    if not hcfg:
        raise SystemExit(f"unknown harness {a.harness}")
    model = a.model or hcfg.get("default_model") or "-"

    rows = load_instances()
    if a.ids:
        want = set(a.ids.split(","))
        rows = [r for r in rows if r["instance_id"] in want]
    elif a.subset:
        with open(a.subset) as f:
            want = {json.loads(l)["instance_id"] for l in f if l.strip()}
        rows = [r for r in rows if r["instance_id"] in want]
    if a.n:
        step = max(len(rows) // a.n, 1)
        rows = rows[::step][: a.n]

    os.makedirs(WORK, exist_ok=True)
    preds_path = a.preds or os.path.join(RESULTS, "swe-mini-predictions.jsonl")
    results_path = os.path.join(RESULTS, "high.jsonl")
    os.makedirs(RESULTS, exist_ok=True)
    timeout_s = a.timeout_min * 60

    print(f"== high tier: {len(rows)} instances, harness={a.harness} model={model} ==")
    done = 0
    for inst in rows:
        iid = inst["instance_id"]
        repo_dir = ensure_repo(inst["repo"])
        wd = os.path.join(WORK, iid)
        log_dir = os.path.join(ROOT, "work", "swe-logs", iid)
        os.makedirs(log_dir, exist_ok=True)
        subprocess.run(["git", "-C", repo_dir, "worktree", "remove", "--force", wd],
                       check=False, capture_output=True)
        rc = subprocess.run(
            ["git", "-C", repo_dir, "worktree", "add", "--detach", wd, inst["base_commit"]],
            capture_output=True, text=True,
        )
        if rc.returncode != 0:
            print(f"❌ {iid}: worktree add failed: {rc.stderr.strip()[:200]}")
            continue

        prompt = (
            inst["problem_statement"]
            + f"\n\nYou are in a checkout of {inst['repo']} at the commit where this issue "
            "applies. Fix the issue by editing the repository. Do not modify tests. "
            "Stop when you believe the issue is fixed."
        )
        cmd = resolve_harness(hcfg, model, wd, prompt)
        t0 = time.time()
        timed_out = False
        with open(os.path.join(log_dir, "agent.log"), "wb") as lf:
            p = subprocess.Popen(cmd, cwd=wd, stdout=lf, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                p.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                import signal, os as _os
                try:
                    _os.killpg(_os.getpgid(p.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
        wall = time.time() - t0

        # capture the patch (tracked edits + new files)
        subprocess.run(["git", "add", "-A"], cwd=wd, check=False, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached"], cwd=wd, check=False,
                              capture_output=True, text=True).stdout
        with open(preds_path, "a") as f:
            f.write(json.dumps({
                "instance_id": iid,
                "model_name_or_path": f"{a.harness}:{model}",
                "model_patch": diff,
            }) + "\n")
        with open(results_path, "a") as f:
            f.write(json.dumps({
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "tier": "high", "task": iid, "trial": 1, "harness": a.harness,
                "model": model, "agent_rc": p.returncode, "agent_timeout": timed_out,
                "agent_wall_s": round(wall, 2), "checker_rc": None,
                "solved": None, "score": None, "patch_bytes": len(diff),
                "run_dir": wd,
            }) + "\n")
        print(f"{'⏱️' if timed_out else '📝'} {iid} wall={wall:.0f}s patch={len(diff)}B -> {preds_path}")
        done += 1
        if not a.keep:
            subprocess.run(["git", "-C", repo_dir, "worktree", "remove", "--force", wd],
                           check=False, capture_output=True)
    print(f"== done: {done}/{len(rows)} patches -> {preds_path} ==")
    print(f"   next: bash bench.sh high eval --preds {preds_path}")
    return 0


# --------------------------------------------------------------------------- eval
def cmd_eval(a) -> int:
    pack = subprocess.run([sys.executable, "-c", "import swebench; print('ok')"],
                          capture_output=True, text=True)
    if "ok" not in pack.stdout:
        print("official SWE-bench harness not installed. Install it first:\n")
        print("  pip3 install --user swebench        # or: python3 -m venv ~/.venvs/swebench && ...")
        print("\nThen rerun:  bash bench.sh high eval")
        print("(needs docker; each instance pulls a ~1-3 GB image)")
        return 2

    preds = a.preds or os.path.join(RESULTS, "swe-mini-predictions.jsonl")
    if not os.path.exists(preds):
        raise SystemExit(f"predictions not found: {preds} — run: bash bench.sh high run ...")
    run_id = a.run_id or dt.datetime.now().strftime("obm-%Y%m%d-%H%M%S")
    cmd = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", DS,
        "--split", "test",
        "--predictions_path", preds,
        "--max_workers", str(a.max_workers),
        "--run_id", run_id,
    ]
    print("+ " + " ".join(cmd), flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode

    # ingest resolved flags
    pats = [
        os.path.join(ROOT, "logs", "run_evaluation", run_id, "**", "report.json"),
        os.path.join(ROOT, "logs", "run_evaluation", run_id, "report.json"),
    ]
    reports = []
    for p in pats:
        reports += glob.glob(p, recursive=True)
    n_ok = n_all = 0
    out_rows = []
    for rp in reports:
        try:
            data = json.load(open(rp))
        except Exception:
            continue
        for iid, v in data.items():
            if not isinstance(v, dict) or "resolved" not in v:
                continue
            n_all += 1
            n_ok += int(bool(v.get("resolved")))
            out_rows.append({
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "tier": "high", "task": iid, "trial": 1, "harness": a.harness,
                "model": a.model or "unknown", "agent_rc": None, "agent_timeout": False,
                "agent_wall_s": None, "checker_rc": 0 if v.get("resolved") else 1,
                "solved": bool(v.get("resolved")), "score": 1.0 if v.get("resolved") else 0.0,
                "run_dir": os.path.dirname(rp),
            })
    if out_rows:
        with open(os.path.join(RESULTS, "high-eval.jsonl"), "a") as f:
            for r in out_rows:
                f.write(json.dumps(r) + "\n")
        print(f"== resolved: {n_ok}/{n_all} (ingested -> results/high-eval.jsonl) ==")
        print("   next: bash bench.sh report --tier high")
    return rc


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch"); f.add_argument("--n", type=int, default=5); f.set_defaults(fn=cmd_fetch)
    sub.add_parser("list").set_defaults(fn=cmd_list)

    r = sub.add_parser("run")
    r.add_argument("--harness", default="opencode")
    r.add_argument("--model", default=None)
    r.add_argument("--n", type=int, default=5)
    r.add_argument("--ids", default=None)
    r.add_argument("--subset", default=None)
    r.add_argument("--timeout-min", type=int, default=30)
    r.add_argument("--preds", default=None)
    r.add_argument("--keep", action="store_true", help="keep git worktrees")
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("eval")
    e.add_argument("--preds", default=None)
    e.add_argument("--max-workers", type=int, default=2)
    e.add_argument("--run-id", default=None)
    e.add_argument("--harness", default="opencode")
    e.add_argument("--model", default="unknown")
    e.set_defaults(fn=cmd_eval)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
