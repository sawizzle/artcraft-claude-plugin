"""End-to-end check of every supported app's MCP server, started through the plugin's own launcher.

    python tests/run_all_tests.py [app ...]

For each installed app it runs tests/steps/<app>.json (create -> edit -> render -> export -> re-read)
over MCP stdio and prints a pass/fail table. Outputs and the returned preview images land in
tests/out/ -- open them: a passing call is not proof the picture is right.
Needs Python 3.9+ and Node 18+. Apps that are not installed are reported and skipped.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAUNCHER = os.path.join(ROOT, "plugins", "creative-apps-mcp", "bin", "craft-mcp.mjs")
IN = os.path.join(HERE, "inputs").replace("\\", "/")
OUT = os.path.join(HERE, "out").replace("\\", "/")

# Server args per app: the same as plugins/creative-apps-mcp/.mcp.json, except PhotoCraft gets explicit test roots
# (its paths are relative to them).
ARGS = {
    "photocraft": ["--automation-read-root", HERE.replace("\\", "/"), "--automation-write-root", OUT],
    "vectorcraft": ["--headless"],
    "filmcraft": [],
    "lightcraft": ["--compact"],
    "pdfcraft": ["--compact"],
    "effectcraft": [],
    "designcraft": [],
}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    node = shutil.which("node")
    if not node:
        sys.exit("node not found on PATH (Node 18+ is required by the plugin launcher)")
    os.makedirs(OUT, exist_ok=True)
    apps = sys.argv[1:] or list(ARGS)
    failed = 0
    for app in apps:
        where = subprocess.run([node, LAUNCHER, app, "--version"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        if where.returncode != 0:
            print(f"{app:12} SKIP  {where.stderr.strip()[:160]}")
            continue
        with open(os.path.join(HERE, "steps", f"{app}.json"), encoding="utf-8") as f:
            steps = f.read().replace("{IN}", IN).replace("{OUT}", OUT)
        resolved = os.path.join(OUT, f"_{app}_steps.json")
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(steps)
        cmd = [node, LAUNCHER, app, "mcp"] + ARGS[app]
        report = os.path.join(OUT, f"{app}_report.json")
        if os.path.exists(report):
            os.remove(report)  # never show a previous run's result as this one
        probe = subprocess.run([sys.executable, os.path.join(HERE, "mcp_probe.py"), "--name", app, "--steps", resolved,
                                "--outdir", OUT, "--cwd", HERE, "--"] + cmd, capture_output=True)
        if probe.returncode != 0 or not os.path.exists(report):
            failed += 1
            print(f"{app:12} PROBE FAILED (exit {probe.returncode}): {probe.stderr.decode(errors='replace').strip()[-300:]}")
            continue
        with open(report, encoding="utf-8") as f:
            r = json.load(f)
        failed += r["failed"] or (0 if r["steps"] else 1)
        version = (r.get("server") or {}).get("version", "?")
        print(f"{app:12} {version:8} {r['passed']} ok / {r['failed']} fail  {r['total_s']}s")
        for s in r["steps"]:
            if not s["ok"]:
                print(f"    step {s['n']} {s['tool']}: {(s.get('text') or json.dumps(s.get('error')))[:200]}")
        if not r["steps"]:
            print(f"    no steps ran: {json.dumps(r.get('init_error'))[:200]} {r.get('stderr_tail')}")
    print(f"\noutputs: {OUT}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
