# stdio MCP probe: initialize -> scripted tools/call steps; image results are saved for a visual check.
# Image content blocks returned by any step are written to <outdir>/<name>_s<N>.png so they can be looked at.
# Usage: python mcp_probe.py --name N --steps steps.json --outdir DIR -- <exe> [args...]
import base64, json, os, subprocess, sys, threading, time, queue

VERSION = "1.0.0"


def main():
    argv = sys.argv[1:]
    sep = argv.index("--")
    opts, cmd = argv[:sep], argv[sep + 1:]
    o = dict(zip(opts[0::2], opts[1::2]))
    name, outdir = o["--name"], o["--outdir"]
    steps = json.load(open(o["--steps"], encoding="utf-8"))
    os.makedirs(outdir, exist_ok=True)

    t0 = time.time()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         cwd=o.get("--cwd"))
    out_q, err_lines = queue.Queue(), []
    threading.Thread(target=lambda: ([out_q.put(l) for l in p.stdout], out_q.put(None)), daemon=True).start()
    threading.Thread(target=lambda: [err_lines.append(l.decode("utf-8", "replace").rstrip()) for l in p.stderr],
                     daemon=True).start()

    def send(obj):
        try:
            p.stdin.write((json.dumps(obj) + "\n").encode()); p.stdin.flush()
        except OSError:
            pass  # the server died; recv() then reports EOF for this step

    def recv(want_id, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                line = out_q.get(timeout=max(0.05, end - time.time()))
            except queue.Empty:
                break
            if line is None:
                return {"_eof": True}
            s = line.decode("utf-8", "replace").strip()
            if not s:
                continue
            try:
                msg = json.loads(s)
            except json.JSONDecodeError:
                return {"_nonjson_stdout": s[:300]}
            if msg.get("id") == want_id:
                return msg
        return {"_timeout": timeout}

    rep = {"name": name, "cmd": cmd, "probe": VERSION, "steps": []}
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "mcp-smoke-probe", "version": VERSION}}})
    r = recv(1, 60)
    if "result" not in r:
        rep["init_error"] = r
    else:
        rep["server"] = r["result"].get("serverInfo")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        for i, st in enumerate(steps, start=1):
            t1 = time.time()
            rid = 100 + i
            send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                  "params": {"name": st["tool"], "arguments": st.get("args", {})}})
            cr = recv(rid, st.get("timeout", 180))
            row = {"n": i, "tool": st["tool"], "s": round(time.time() - t1, 2)}
            res = cr.get("result")
            if res is None:
                row["ok"] = False
                row["error"] = cr.get("error", cr)
            else:
                row["ok"] = not res.get("isError", False)
                texts, imgs = [], []
                for c in res.get("content", []):
                    if c.get("type") == "text":
                        texts.append(c.get("text", ""))
                    elif c.get("type") == "image":
                        ext = {"image/png": "png", "image/jpeg": "jpg"}.get(c.get("mimeType"), "bin")
                        fp = os.path.join(outdir, f"{name}_s{i}.{ext}")
                        with open(fp, "wb") as f:
                            f.write(base64.b64decode(c["data"]))
                        imgs.append(fp)
                row["text"] = " ".join(texts)[:700]
                if imgs:
                    row["images"] = imgs
            rep["steps"].append(row)
    try:
        try:
            p.stdin.close()
        except OSError:
            pass
        p.wait(timeout=15); rep["exit"] = p.returncode
    except subprocess.TimeoutExpired:
        p.kill(); rep["exit"] = "HUNG (killed)"
    rep["total_s"] = round(time.time() - t0, 2)
    rep["stderr_tail"] = err_lines[-6:]
    rep["passed"] = sum(1 for s in rep["steps"] if s["ok"])
    rep["failed"] = sum(1 for s in rep["steps"] if not s["ok"])
    with open(os.path.join(outdir, f"{name}_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
