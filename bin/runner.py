#!/usr/bin/env python3
"""Agent benchmark runner.

Flow per cell:  copy task workspace/ -> run the agent harness (opencode/codex/...)
inside that copy -> run the task checker (cwd = the copy, TASK_DIR = pristine task
dir) -> append one JSONL record (score, wall time, tokens/cost when the harness
reports them).

Tiers (config/tiers.json):
  low  = openbench core mini-repos   (default 3 tasks x 3 trials)
  mid  = openbench imported Terminal-Bench subset (default 3 tasks x 1 trial)

Selftest (zero LLM cost): every task must FAIL untouched (dry-none) and PASS with
the golden solution overlaid (dry-solution).

Examples:
  python3 bin/runner.py --tier low --harness opencode --model provider/model --trials 1
  python3 bin/runner.py --selftest -v
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "tasks")
WORK_DIR = os.path.join(ROOT, "work")


def set_work_dir(path: str) -> None:
    """Point the per-cell workspaces outside the benchmark repo.

    When cells live under the repo, opencode's project root is the repo root, so the
    agent can (and did, on 2026-10-19) reach tasks/, solution/ and checker data. An
    external work dir makes the run dir itself the project root.
    """
    global WORK_DIR
    WORK_DIR = os.path.abspath(os.path.expanduser(path))
RESULTS_DIR = os.path.join(ROOT, "results")

SCORE_RE = re.compile(r"SCORE:\s*([0-9]*\.?[0-9]+)")


# --------------------------------------------------------------------------- utils
def now_ts() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def discover_opencode() -> str:
    env = os.environ.get("OPENCODE_BIN")
    if env:
        return env
    p = shutil.which("opencode")
    if p:
        return p
    cands = sorted(glob.glob(os.path.expanduser("~/.opencode/desktop-ssh/*/opencode")))
    return cands[-1] if cands else "opencode"


def resolve_bin(name: str) -> str:
    if not name:
        return ""
    if name == "AUTO_OPENCODE":
        return discover_opencode()
    name = os.path.expanduser(name)
    if os.path.isabs(name):
        return name
    return shutil.which(name) or name


def task_dir(tier: str, task: str) -> str:
    return os.path.join(TASKS_DIR, tier, task)


def make_run_dir(tier: str, task: str, label: str) -> str:
    d = os.path.join(WORK_DIR, tier, task, f"{label}-{now_ts()}")
    os.makedirs(d, exist_ok=True)
    return d


def copy_workspace(src_task: str, run_dir: str) -> None:
    ws = os.path.join(src_task, "workspace")
    if not os.path.isdir(ws):
        raise SystemExit(f"task has no workspace/: {src_task}")
    for entry in os.listdir(ws):
        s = os.path.join(ws, entry)
        d = os.path.join(run_dir, entry)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True)
        else:
            shutil.copy2(s, d)


def overlay_solution(src_task: str, run_dir: str) -> None:
    sol = os.path.join(src_task, "solution")
    if not os.path.isdir(sol):
        raise SystemExit(f"task has no solution/: {src_task}")
    for base, _dirs, files in os.walk(sol):
        for f in files:
            s = os.path.join(base, f)
            rel = os.path.relpath(s, sol)
            d = os.path.join(run_dir, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)


def init_isolated_repo(run_dir: str) -> None:
    """Pin the cell as its own git project root.

    opencode resolves a session's project root from the git worktree; a plain
    directory under an existing project can be mapped back to that project (on
    2026-10-20 a cell ran with cwd ~/agent_benchmark instead of its own workspace,
    which lets the agent read tasks/, solution/ and checker.sh). A local repo makes
    the run dir the project root.
    """
    git = shutil.which("git")
    if not git:
        return
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="bench",
        GIT_AUTHOR_EMAIL="bench@local",
        GIT_COMMITTER_NAME="bench",
        GIT_COMMITTER_EMAIL="bench@local",
    )
    subprocess.run([git, "init", "-q"], cwd=run_dir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([git, "add", "-A"], cwd=run_dir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([git, "commit", "-qm", "bench baseline", "--no-gpg-sign"], cwd=run_dir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------------- exec
def run_cmd(cmd: list[str], cwd: str, timeout_s: int, log_path: str, env: dict | None = None):
    """Run cmd, tee all output to log_path. Returns (rc, wall_s, timed_out, output)."""
    t0 = time.time()
    timed_out = False
    full_env = dict(os.environ)
    if env:
        for k, v in env.items():
            if v is None:
                full_env.pop(k, None)
            else:
                full_env[k] = v
    # python's cwd= does not update PWD; opencode resolves its location from $PWD,
    # so a stale PWD makes the tested agent run in the parent shell's directory.
    full_env["PWD"] = cwd
    full_env.pop("OLDPWD", None)
    with open(log_path, "wb") as lf:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=full_env,
            start_new_session=True,
        )
        try:
            out, _ = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, _ = proc.communicate()
        lf.write(out or b"")
    wall = time.time() - t0
    return proc.returncode, wall, timed_out, (out or b"").decode("utf-8", "replace")


def extract_usage(text: str) -> dict:
    """Best-effort numeric usage extraction from harness stdout (JSON or JSONL).

    Handles: opencode `--format json` step_finish events (summed across steps) and
    generic JSON/JSONL usage keys (codex `--json`, vendor APIs, ...).
    """
    found = {
        "tokens_input": None,
        "tokens_output": None,
        "tokens_cache_read": None,
        "tokens_total": None,
        "cost_usd": None,
    }

    # opencode: {"part": {"type": "step-finish", "tokens": {...}, "cost": N}}
    tin = tout = tcache = tcost = 0
    seen_opencode = False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = obj.get("part") if isinstance(obj, dict) else None
        if isinstance(part, dict) and isinstance(part.get("tokens"), dict):
            t = part["tokens"]
            seen_opencode = True
            tin += t.get("input") or 0
            tout += (t.get("output") or 0) + (t.get("reasoning") or 0)
            cache = t.get("cache") or {}
            tcache += cache.get("read") or 0
            tcost += part.get("cost") or 0
    if seen_opencode:
        found["tokens_input"] = tin
        found["tokens_output"] = tout
        found["tokens_cache_read"] = tcache
        found["tokens_total"] = tin + tout
        found["cost_usd"] = tcost
        return found
    keys = {
        "input_tokens": "tokens_input",
        "prompt_tokens": "tokens_input",
        "output_tokens": "tokens_output",
        "completion_tokens": "tokens_output",
        "total_tokens": "tokens_total",
        "cost": "cost_usd",
        "cost_usd": "cost_usd",
        "total_cost": "cost_usd",
    }

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                tgt = keys.get(k)
                if tgt and isinstance(v, (int, float)):
                    if found[tgt] is None or (tgt == "cost_usd" and v > found[tgt]):
                        found[tgt] = v
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    objs = []
    try:
        objs.append(json.loads(text))
    except Exception:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("{", "[")):
                try:
                    objs.append(json.loads(line))
                except Exception:
                    pass
    for o in objs:
        walk(o)
    if found["tokens_total"] is None and (
        found["tokens_input"] is not None or found["tokens_output"] is not None
    ):
        found["tokens_total"] = (found["tokens_input"] or 0) + (found["tokens_output"] or 0)
    return found


# ----------------------------------------------------------- subagent accounting
SID_RE = re.compile(r'"sessionID"\s*:\s*"(ses_[A-Za-z0-9]+)"')


def opencode_db_path() -> str:
    """opencode v2 keeps sessions in a sqlite db (no OPENCODE_DB override => default)."""
    return os.environ.get("OPENCODE_DB") or os.path.expanduser(
        "~/.local/share/opencode/opencode.db"
    )


def main_session_id(agent_out: str) -> str | None:
    m = SID_RE.search(agent_out or "")
    return m.group(1) if m else None


def collect_session_usage(main_sid: str, db_path: str | None = None) -> dict | None:
    """Sum token usage of the main session plus every descendant (subagent) session.

    `opencode run --format json` only prints step-finish events of the parent session;
    agents launched through the `subagent` tool run in child sessions, so their tokens
    are invisible to extract_usage(). Read them back from the sqlite session store and
    aggregate along parent_id.
    """
    if not main_sid:
        return None
    path = db_path or opencode_db_path()
    if not path or not os.path.exists(path):
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        con.row_factory = sqlite3.Row
    except sqlite3.Error:
        return None
    rows: list[dict] = []
    try:
        seen = {main_sid}
        frontier = [main_sid]
        while frontier:
            q = (
                "SELECT id,parent_id,agent,model,tokens_input,tokens_output,"
                "tokens_reasoning,tokens_cache_read FROM session_v2 WHERE id IN ("
                + ",".join("?" * len(frontier))
                + ")"
            )
            fetched = {r["id"]: dict(r) for r in con.execute(q, frontier).fetchall()}
            rows.extend(fetched.values())
            nxt = []
            for r in fetched.values():
                for c in con.execute(
                    "SELECT id FROM session_v2 WHERE parent_id=?", (r["id"],)
                ).fetchall():
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        nxt.append(c["id"])
            frontier = nxt
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not rows:
        return None

    def n(r, k):
        return int(r.get(k) or 0)

    sessions = [
        {
            "id": r["id"],
            "parent_id": r["parent_id"],
            "agent": r["agent"],
            "model": r["model"],
            "in": n(r, "tokens_input"),
            # align with extract_usage(): output already includes reasoning there
            "out": n(r, "tokens_output") + n(r, "tokens_reasoning"),
            "reasoning": n(r, "tokens_reasoning"),
            "cache": n(r, "tokens_cache_read"),
        }
        for r in rows
    ]
    subs = [s for s in sessions if s["id"] != main_sid]
    return {
        "sessions": sessions,
        "sessions_total": len(sessions),
        "sessions_subagent": len(subs),
        "subagents": [
            {"id": s["id"], "agent": s["agent"], "in": s["in"], "out": s["out"]} for s in subs
        ],
        "all_tokens_input": sum(s["in"] for s in sessions),
        "all_tokens_output": sum(s["out"] for s in sessions),
        "all_tokens_reasoning": sum(s["reasoning"] for s in sessions),
        "all_tokens_cache_read": sum(s["cache"] for s in sessions),
        "all_tokens_total": sum(s["in"] + s["out"] for s in sessions),
        "subagent_tokens_input": sum(s["in"] for s in subs),
        "subagent_tokens_output": sum(s["out"] for s in subs),
        "subagent_tokens_total": sum(s["in"] + s["out"] for s in subs),
    }


def run_checker(src_task: str, run_dir: str, log_path: str):
    env = dict(os.environ)
    env["TASK_DIR"] = src_task
    rc, wall, timed_out, out = run_cmd(
        ["bash", os.path.join(src_task, "checker.sh")], run_dir, 900, log_path, env
    )
    m = SCORE_RE.search(out)
    score = float(m.group(1)) if m else None
    return rc, wall, timed_out, out, score


# --------------------------------------------------------------------------- plan
def build_cells(tier_cfg: dict, tier: str, tasks: list[str] | None, trials: int | None):
    names = tasks or tier_cfg["tasks"]
    n = trials if trials else int(tier_cfg.get("trials", 1))
    return [(t, k + 1) for t in names for k in range(n)]


def build_prompt(src_task: str, tier_cfg: dict) -> str:
    with open(os.path.join(src_task, "instruction.md")) as f:
        instr = f.read().strip()
    return instr + tier_cfg.get("prompt_suffix", "")


def harness_cmd(cfg: dict, model: str, workdir: str, prompt: str) -> list[str]:
    bin_path = resolve_bin(cfg.get("bin", ""))
    args = [
        a.replace("{model}", model)
        .replace("{workdir}", workdir)
        .replace("{prompt}", prompt)
        for a in cfg.get("args", [])
    ]
    return ([bin_path] if bin_path else []) + args


# --------------------------------------------------------------------------- cell
def run_cell(tier, task, trial, harness_name, hcfg, model, tier_cfg, results_path, verbose,
             prompt_extra: str = "", agent_env: dict | None = None, session_accounting: bool = True,
             isolated_repo: bool = True):
    src = task_dir(tier, task)
    run_dir = make_run_dir(tier, task, f"{harness_name}-t{trial}")
    log_dir = os.path.join(run_dir, ".bench")
    os.makedirs(log_dir, exist_ok=True)
    copy_workspace(src, run_dir)
    if isolated_repo:
        init_isolated_repo(run_dir)

    prompt = build_prompt(src, tier_cfg) + (prompt_extra or "")
    timeout_s = int(tier_cfg.get("timeout_min", 30)) * 60

    agent_rc, agent_wall, agent_to, agent_out = (None, 0.0, False, "")
    usage = {}
    session_usage = None

    if harness_name == "dry-none":
        pass
    elif harness_name == "dry-solution":
        overlay_solution(src, run_dir)
    else:
        cmd = harness_cmd(hcfg, model, run_dir, prompt)
        if not cmd or not os.path.exists(cmd[0]):
            raise SystemExit(
                f"harness binary not found: {cmd[:1]} — set OPENCODE_BIN or install the CLI"
            )
        # do not leak this session's opencode identity into the tested agent
        cell_env = dict(agent_env or {})
        for k in ("OPENCODE_SESSION_ID", "AI_AGENT", "OPENCODE", "OPENCODE_TERMINAL",
                  "BILLION_CONTEXT_NATIVE"):
            cell_env.setdefault(k, None)
        agent_rc, agent_wall, agent_to, agent_out = run_cmd(
            cmd, run_dir, timeout_s, os.path.join(log_dir, "agent.log"), cell_env
        )
        usage = extract_usage(agent_out)
        session_usage = None
        if session_accounting:
            session_usage = collect_session_usage(main_session_id(agent_out))

    chk_rc, chk_wall, chk_to, chk_out, score = run_checker(
        src, run_dir, os.path.join(log_dir, "checker.log")
    )
    solved = chk_rc == 0

    row = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "tier": tier,
        "task": task,
        "trial": trial,
        "harness": harness_name,
        "model": model,
        "agent_rc": agent_rc,
        "agent_timeout": agent_to,
        "agent_wall_s": round(agent_wall, 2),
        "checker_rc": chk_rc,
        "checker_timeout": chk_to,
        "solved": solved,
        "score": score,
        "tokens_input": usage.get("tokens_input"),
        "tokens_output": usage.get("tokens_output"),
        "tokens_cache_read": usage.get("tokens_cache_read"),
        "tokens_total": usage.get("tokens_total"),
        "cost_usd": usage.get("cost_usd"),
        "run_dir": run_dir,
    }
    if prompt_extra:
        row["prompt_extra"] = prompt_extra
    if session_usage:
        row.update(
            {
                "sessions_total": session_usage["sessions_total"],
                "sessions_subagent": session_usage["sessions_subagent"],
                "subagents": session_usage["subagents"],
                "all_tokens_input": session_usage["all_tokens_input"],
                "all_tokens_output": session_usage["all_tokens_output"],
                "all_tokens_reasoning": session_usage["all_tokens_reasoning"],
                "all_tokens_cache_read": session_usage["all_tokens_cache_read"],
                "all_tokens_total": session_usage["all_tokens_total"],
                "subagent_tokens_input": session_usage["subagent_tokens_input"],
                "subagent_tokens_output": session_usage["subagent_tokens_output"],
                "subagent_tokens_total": session_usage["subagent_tokens_total"],
            }
        )
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "a") as f:
        f.write(json.dumps(row) + "\n")

    icon = "✅" if solved else ("⏱️" if (agent_to or chk_to) else "❌")
    extra = f" score={score:.2f}" if score is not None else ""
    tok = f" tok={row['tokens_total']}" if row["tokens_total"] else ""
    if session_usage:
        tok += f" all={session_usage['all_tokens_total']}"
        if session_usage["sessions_subagent"]:
            tok += f" sub={session_usage['sessions_subagent']}(+{session_usage['subagent_tokens_total']})"
    print(
        f"{icon} [{tier}/{task} t{trial}] {harness_name} wall={agent_wall:.0f}s{extra}{tok} -> {run_dir}",
        flush=True,
    )
    if verbose and not solved:
        tail = chk_out.strip().splitlines()[-6:]
        for line in tail:
            print(f"    | {line}")
    return row, solved


# --------------------------------------------------------------------------- selftest
def selftest(args, tiers) -> int:
    rc_all = 0
    for tier in tiers:
        cfg = load_json(os.path.join(ROOT, "config", "tiers.json"))[tier]
        for task in cfg["tasks"]:
            src = task_dir(tier, task)
            fails = []
            for harness, expect_ok in (("dry-none", False), ("dry-solution", True)):
                row, solved = run_cell(
                    tier,
                    task,
                    0,
                    harness,
                    {"bin": "", "args": []},
                    "-",
                    cfg,
                    os.path.join(RESULTS_DIR, "selftest.jsonl"),
                    args.verbose,
                )
                if solved != expect_ok:
                    fails.append(harness)
            status = "✅" if not fails else f"❌ ({','.join(fails)})"
            print(f"selftest [{tier}/{task}] {status}", flush=True)
            if fails:
                rc_all = 1
    print("selftest " + ("PASSED ✅" if rc_all == 0 else "FAILED ❌"))
    return rc_all


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["low", "mid"])
    ap.add_argument("--harness", default="opencode")
    ap.add_argument("--model", default=None)
    ap.add_argument("--tasks", default=None, help="comma-separated task subset")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--timeout-min", type=int, default=None)
    ap.add_argument("--results", default=None)
    ap.add_argument("--prompt-extra", default="",
                    help="extra text appended to the task prompt (recorded in results)")
    ap.add_argument("--opencode-config", default=None,
                    help="JSON file injected as OPENCODE_CONFIG_CONTENT for the agent process")
    ap.add_argument("--no-session-accounting", action="store_true",
                    help="do not add child/subagent session tokens to the record")
    ap.add_argument("--work-dir", default=None,
                    help="override work/ (keep cells outside the repo so the agent cannot reach tasks/)")
    ap.add_argument("--no-isolated-repo", action="store_true",
                    help="do not git-init each cell (cells may then inherit an enclosing project root)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selftest-tiers", default="low,mid")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.work_dir:
        set_work_dir(args.work_dir)

    tiers_all = load_json(os.path.join(ROOT, "config", "tiers.json"))
    harnesses = load_json(os.path.join(ROOT, "config", "harnesses.json"))

    if args.selftest:
        return selftest(args, args.selftest_tiers.split(","))

    if not args.tier:
        ap.error("--tier is required (or use --selftest)")

    cfg = dict(tiers_all[args.tier])
    if args.timeout_min:
        cfg["timeout_min"] = args.timeout_min
    hcfg = harnesses.get(args.harness)
    if hcfg is None:
        raise SystemExit(f"unknown harness {args.harness}; options: {', '.join(harnesses)}")

    model = args.model or hcfg.get("default_model") or "-"
    tasks = args.tasks.split(",") if args.tasks else None
    cells = build_cells(cfg, args.tier, tasks, args.trials)
    results_path = args.results or os.path.join(RESULTS_DIR, f"{args.tier}.jsonl")

    print(f"== tier={args.tier} harness={args.harness} model={model} cells={len(cells)} ==")
    print(f"   results: {results_path}")
    agent_env = None
    if args.opencode_config:
        with open(os.path.expanduser(args.opencode_config)) as f:
            agent_env = {"OPENCODE_CONFIG_CONTENT": f.read()}
        print(f"   opencode config injected: {args.opencode_config}")
    if args.prompt_extra:
        print(f"   prompt extra: {args.prompt_extra!r}")
    if not args.no_session_accounting:
        print("   session accounting: main + subagent child sessions")
    solved_n = 0
    t0 = time.time()
    for task, trial in cells:
        _row, ok = run_cell(
            args.tier, task, trial, args.harness, hcfg, model, cfg, results_path, args.verbose,
            args.prompt_extra, agent_env, not args.no_session_accounting,
            not args.no_isolated_repo,
        )
        solved_n += int(ok)
    print(f"== done: {solved_n}/{len(cells)} solved in {time.time() - t0:.0f}s ==")
    print(f"   next: bash bench.sh report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
