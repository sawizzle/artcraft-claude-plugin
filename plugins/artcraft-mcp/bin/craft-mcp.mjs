#!/usr/bin/env node
// craft-mcp: find an ArtCraft app's CLI and run it, passing stdio straight through.
//   node craft-mcp.mjs <app> [args...]        e.g. node craft-mcp.mjs photocraft mcp
//   node craft-mcp.mjs --where                 print where each CLI was found (setup check)
// Lookup order: $<APP>_CLI (must exist if set), then absolute PATH entries, then the platform's
// install locations. Nothing is written to stdout except the child's output, so the MCP stream stays clean.
import { spawn } from "node:child_process";
import { accessSync, constants, mkdirSync, statSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

const VERSION = "0.1.0";

const APPS = {
  photocraft: "PhotoCraft",
  vectorcraft: "VectorCraft",
  filmcraft: "FilmCraft",
  lightcraft: "LightCraft",
  pdfcraft: "PdfCraft",
  effectcraft: "EffectCraft",
  designcraft: "DesignCraft",
};

const isWin = process.platform === "win32";
const exe = (app) => `${app}-cli${isWin ? ".exe" : ""}`;
const unquote = (s) => s.trim().replace(/^"(.*)"$/, "$1");

function runnable(p) {
  try {
    if (!statSync(p).isFile()) return false;
    if (!isWin) accessSync(p, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function fail(msg) {
  process.stderr.write(`craft-mcp: ${msg}\n`);
  process.exit(1);
}

// $<APP>_CLI is an explicit choice: if it is set but wrong, say so instead of quietly using something else.
function fromEnv(app) {
  const name = `${app.toUpperCase()}_CLI`;
  const v = process.env[name] ? unquote(process.env[name]) : "";
  if (!v) return null;
  if (!runnable(v)) fail(`${name}=${v} is not an executable file`);
  return v;
}

function candidates(app) {
  const Name = APPS[app];
  const bin = exe(app);
  const out = [];
  // Only absolute PATH entries: a relative one would resolve against the project folder.
  for (const raw of (process.env.PATH || "").split(path.delimiter)) {
    const dir = unquote(raw);
    if (dir && path.isAbsolute(dir)) out.push(path.join(dir, bin));
  }
  const home = homedir();
  if (isWin) {
    for (const base of [process.env.ProgramFiles, process.env.ProgramW6432, process.env["ProgramFiles(x86)"]]) {
      if (base) out.push(path.join(base, Name, bin));
    }
    if (process.env.LOCALAPPDATA) out.push(path.join(process.env.LOCALAPPDATA, "Programs", Name, bin));
  } else if (process.platform === "darwin") {
    // The macOS CLI ships as its own zip (it is not inside the .app); these are the usual homes.
    for (const dir of ["/opt/homebrew/bin", "/usr/local/bin", path.join(home, ".local", "bin"), path.join(home, "bin")]) {
      out.push(path.join(dir, bin));
    }
  } else {
    for (const dir of ["/usr/bin", "/usr/local/bin", path.join(home, ".local", "bin")]) {
      out.push(path.join(dir, bin));
    }
  }
  return out;
}

function resolveCli(app) {
  return fromEnv(app) || candidates(app).find(runnable) || null;
}

// An unset plugin option can arrive empty or as an unexpanded "${user_config.*}"; treat both as unset.
const setting = (...names) => {
  for (const n of names) {
    const v = unquote(process.env[n] || "");
    if (v && !v.startsWith("${")) return v;
  }
  return "";
};

const hasFlag = (args, flag) => args.some((a) => a === flag || a.startsWith(`${flag}=`));

// PhotoCraft has no file access unless it is given roots, and its tool paths are relative to them.
// Read root: plugin option, else $PHOTOCRAFT_READ_ROOT, else the home folder.
// Write root: plugin option, else $PHOTOCRAFT_WRITE_ROOT, else a dedicated ~/PhotoCraft folder
// (never the whole home folder: an export may overwrite any file under the write root).
function withDefaults(app, args) {
  if (app !== "photocraft" || args[0] !== "mcp" || hasFlag(args, "--bridge")) return args;
  const a = [...args];
  const fwd = (p) => p.replace(/\\/g, "/");
  if (!hasFlag(a, "--automation-read-root")) {
    const read = setting("CRAFT_OPT_PHOTOCRAFT_READ_ROOT", "PHOTOCRAFT_READ_ROOT") || homedir();
    a.push("--automation-read-root", fwd(read));
  }
  if (!hasFlag(a, "--automation-write-root")) {
    let write = setting("CRAFT_OPT_PHOTOCRAFT_WRITE_ROOT", "PHOTOCRAFT_WRITE_ROOT");
    if (!write) {
      write = path.join(homedir(), "PhotoCraft");
      try {
        mkdirSync(write, { recursive: true });
      } catch (e) {
        fail(`cannot create PhotoCraft write root ${write}: ${e.message}`);
      }
    }
    a.push("--automation-write-root", fwd(write));
  }
  return a;
}

function main() {
  const [app, ...rest] = process.argv.slice(2);
  if (app === "--version") {
    process.stderr.write(`craft-mcp ${VERSION}\n`);
    return;
  }
  if (app === "--where") {
    for (const a of Object.keys(APPS)) {
      let found;
      try {
        found = fromEnv(a) || candidates(a).find(runnable);
      } catch {
        found = null;
      }
      process.stderr.write(`${a.padEnd(12)} ${found || "NOT FOUND"}\n`);
    }
    return;
  }
  if (!app || !APPS[app]) {
    process.stderr.write(`craft-mcp: usage: craft-mcp <${Object.keys(APPS).join("|")}> [args...] | --where\n`);
    process.exit(2);
  }
  const cli = resolveCli(app);
  if (!cli) {
    fail(
      `${exe(app)} not found. Install ${APPS[app]} from https://getartcraft.com/apps/${app}, ` +
        `put ${exe(app)} on PATH, or set ${app.toUpperCase()}_CLI to its full path.`,
    );
  }
  const child = spawn(cli, withDefaults(app, rest), { stdio: "inherit", windowsHide: true });
  child.on("error", (e) => fail(`failed to start ${cli}: ${e.message}`));
  child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
  for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.on(sig, () => {
      if (!child.killed) child.kill(sig);
    });
  }
}

// Always run: this file is only ever executed, never imported (an import.meta/argv comparison breaks
// when the plugin directory is reached through a symlink or junction).
main();
