---
name: photocraft
description: Drive PhotoCraft (open-source Photoshop-style raster editor) through its MCP server — open/create images, run engine commands (filters, adjustments, layers), preview, and export PSD/PNG/JPEG/TIFF/WebP/EXR. Use when the user wants to edit, filter, convert or batch-process raster images with PhotoCraft, or when a photocraft tool call fails on a path.
---

# PhotoCraft via MCP

Server: `photocraft` (`photocraft-cli mcp`). Tested with photocraft-cli 0.5.0 on Windows 11. Headless by default; see
the `artcraft-setup` skill for driving the live window.

## The one rule that trips everyone: paths
- PhotoCraft has **no file access** unless it's started with `--automation-read-root` and
  `--automation-write-root`.
- This plugin sets the roots from its options (`photocraft_read_root` / `photocraft_write_root`), then
  from `$PHOTOCRAFT_READ_ROOT` / `$PHOTOCRAFT_WRITE_ROOT`.
- If neither is set, the read root is the **home folder** and the write root is **`~/PhotoCraft`**. An
  export can overwrite any file under the write root, which is why it isn't the whole home folder.
- A root that doesn't exist stops the server from starting.
- Every `path` must be **relative, with forward slashes and no drive letter**:
  - `doc_open` paths are relative to the **read** root.
  - `doc_export` / `doc_save` paths are relative to the **write** root.
  - With the read root at `/Users/me`, open `Pictures/a.png`, not `/Users/me/Pictures/a.png` or `C:/...`.
  - With the default write root (`~/PhotoCraft`), `doc_export {"path":"out.png"}` writes `~/PhotoCraft/out.png`.
  Absolute paths are rejected with "drive, device and stream prefixes are not allowed"
  (storytold/photocraft#2176).
- `../` is rejected. To reach other folders, set the plugin options with `/plugin` → artcraft-mcp →
  configure, or with `claude plugin configure ... --values-stdin`, then restart the session.

## Tested workflow
1. `doc_open {"path":"Pictures/in.png"}` → `{index, width, height, layers, warnings}`
   (or `doc_new {"width":800,"height":600,"background":"#3366ff"}`)
2. `command_list {"filter":"gaussian"}` gives the command id and its params doc, e.g.
   `filter.blur.gaussianBlur {"radius":0.1..1000=1}`
3. `command_run {"id":"filter.blur.gaussianBlur","params":{"radius":12}}`
4. `doc_render_preview {"max_side":1024}` returns a PNG. **Look at it before you export.**
5. `doc_export {"path":"Pictures/out.png"}`; the extension picks the format. Use `quality` for JPEG/WebP.
   `doc_save` with no `path` writes back to the source file. That works only for PSD, PSB and .pcraft files
   kept in their own format.

## Other tools
- **Documents:** `doc_inspect` (layer tree, history, selection), `doc_select`, `doc_close`, `doc_save`,
  `session_list`.
- **Long commands:** `command_batch` runs several commands in one call. For long filters, Content-Aware Fill
  and Photomerge, call `command_run` with `"wait": false` → `{job}`, then poll `jobs_list`, or stop it with
  `jobs_cancel`.
- **Live mode only:** `ui_*` and `control_call` work only with `--bridge`, which needs a control token.

## Without MCP
`photocraft-cli` also has a headless CLI:
- `photocraft-cli convert in.psd out.png`
- `photocraft-cli info file`
- `photocraft-cli run file --cmd <id> --params '{...}' --out out.png`
- `photocraft-cli batch --actions a.json --in dir --out dir`
- droplets
