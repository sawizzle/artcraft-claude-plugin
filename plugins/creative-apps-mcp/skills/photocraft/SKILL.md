---
name: photocraft
description: Unofficial third-party skill. Drive PhotoCraft (open-source Photoshop-style raster editor) through its MCP server — open/create images, run engine commands (filters, adjustments, layers), preview, and export PSD/PNG/JPEG/TIFF/WebP/EXR, headless or live in the app window. Use when the user wants to edit, filter, convert or batch-process raster images with PhotoCraft, watch or assist edits in the open PhotoCraft window, or when a photocraft tool call fails on a path.
---

# PhotoCraft via MCP

Server: `photocraft` (`photocraft-cli mcp`). Tested with photocraft-cli 0.6.0 on Windows 11 only (macOS and Linux
not tested). Headless by default (the headless CLI links no GPU API, so it runs on the CPU). See the `creative-apps-setup`
skill for the live-window flags.

## How to work
1. **Health check first:** `doc_new {"width":800,"height":600,"background":"#3366ff"}` then `doc_render_preview`, and
   look at the image. In live mode, `session_list` is the check.
2. **Read back after every edit.** A reply of ok is not proof: wrong or unknown params often run anyway (see Traps).
3. **Look at renders before you export or report.** Convert to sRGB before judging colour in a preview (see below).

## Paths: the rule that trips everyone
- PhotoCraft has **no file access** unless it's started with `--automation-read-root` and
  `--automation-write-root`.
- This plugin sets the roots from its options (`photocraft_read_root` / `photocraft_write_root`), then
  from `$PHOTOCRAFT_READ_ROOT` / `$PHOTOCRAFT_WRITE_ROOT`.
- If neither is set, the read root is the **home folder** (the agent can read any image under it; a narrower
  `photocraft_read_root` is safer) and the write root is **`~/PhotoCraft`**. An export can overwrite any file under
  the write root, which is why it isn't the whole home folder.
- A root that doesn't exist stops the server from starting.
- Every `path` must be **relative, with forward slashes and no drive letter**:
  - `doc_open` paths are relative to the **read** root.
  - `doc_export` / `doc_save` paths are relative to the **write** root.
  - With the read root at `/Users/me`, open `Pictures/a.png`, not `/Users/me/Pictures/a.png` or `C:/...`.
  - With the default write root (`~/PhotoCraft`), `doc_export {"path":"out.png"}` writes `~/PhotoCraft/out.png`.
- Rejected: absolute paths ("drive, device and stream prefixes are not allowed", storytold/photocraft#2176, not
  re-checked and may change in a later release), `..`, `\`, `:` (streams), `| ? * <`, and reserved Windows names
  (`CON`, `NUL`, `COM1`, `LPT1`, `CONIN$`).
- Missing parent folders are **not** created (NotFound). Overwrites are **silent**: the reply is just `{path, warnings}`.
- Long roots, spaces, accented and CJK names, and full paths over 260 chars work. **Junctions and symlinks under
  the root are refused** ("a path led outside of the filesystem"), even when they point inside it. A junction given
  as the root itself is accepted.
- To reach other folders, set the plugin options with `/plugin` → creative-apps-mcp → configure, or with
  `claude plugin configure ... --values-stdin`, then restart the session.

## Tested workflow
1. `doc_open {"path":"Pictures/in.png"}` → `{index, name, width, height, layers, warnings}` (or `doc_new`).
   EXIF orientation is applied on open; EXR opens as 32-bit "Linear sRGB".
2. `command_list {"filter":"gaussian"}` gives the command id and its params doc, e.g.
   `filter.blur.gaussianBlur {"radius":0.1..1000=1}`
3. `command_run {"id":"filter.blur.gaussianBlur","params":{"radius":12}}`. Compare the effective params in the
   reply (e.g. `{"filter":{"filter":"gaussianBlur","radius":12.0},"layer":2}`) with what you sent.
4. `doc_render_preview {"max_side":1024}` returns a PNG. **Look at it before you export.**
5. `doc_export {"path":"Pictures/out.png"}`; the extension picks the format. Use `quality` for JPEG/WebP.
6. `doc_save`: **always pass `path`** (write-root relative; `.pcraft` is lossless native). Without `path`, the
   read-root-relative source path is resolved under the **write** root, so when the roots differ (the plugin
   defaults do) it writes a NEW file (or overwrites a same-named one) under the write root, and fails NotFound if
   the sub-folder is missing there. It is only safe when both roots are the same folder.

## Traps (verified on 0.6.0, Windows 11 only)
- **Params are only partly validated.** Most filters run a wrong type, misspelled key or `null` at the default;
  out-of-range values are clamped. Adjustments and `edit.fill` reject wrong types and unknown enum values, but still
  clamp numbers and ignore unknown keys. A misspelled adjustment key is a no-op that still adds a history step.
- **Colours:** pass `"#rrggbb"`. Arrays are read as 0..1, so `[128,128,128]` paints **white** in `edit.fill`,
  `tools.setColors` and `layer.newFillLayer.solidColor` (param `color`).
- **`layer` must be an integer id from `doc_inspect`.** A name or numeric string is silently ignored, and
  setProps, delete and rename then act on the **active** layer. `select.findLayers` is a case-insensitive substring
  match (`Layer 1` also matches `Layer 10`).
- **Layer ids** are stable across undo/redo and never reused (a stale id errors "no such layer"). `.pcraft` keeps
  ids across save and reopen; PSD renumbers them. A reopened `.pcraft` can report its pre-save `name`, so key
  documents on `path`.
- **`command_batch`** returns `isError:false` even when a step fails: check `completed`, `failed` and `results[].ok`.
  It stops at the first failing step (later steps do not run). It is not atomic (one history step per command);
  undoing exactly `completed` times restores the pre-batch state.
- **History:** `revision` rises on every edit, undo and redo. History lists states only up to the current one
  (`canRedo` shows the rest). `doc_inspect` has `revision` but no `dirty`.
- **Jobs:** `command_run` with `"wait": false` → `{job, pending:true}`. `jobs_list` states are running, done and
  cancelled, with progress 0..1; `jobs_cancel` leaves the document unchanged. **Always pass the `job` id:** with none,
  it cancels every running job. **Poll to done before exporting:**
  `doc_export` during a job writes the pre-job pixels with no warning. Closing the server drops running jobs silently.
- **Preview limits:** `doc_render_preview` rejects `max_side` above 2048 (default 1024) and refuses documents over
  67,108,864 px even with a small `max_side`. It writes raw document values into an untagged PNG, so
  Linear-sRGB/EXR and ProPhoto/Adobe RGB documents preview wrong. Run `edit.convertToProfile {"profile":"srgb"}`
  first, then preview (verified exact). An exported PNG embeds the ICC profile only for non-sRGB documents, its
  pixels stay raw, and it looks right only in a colour-managed viewer.
- **Notes** have no ids, only a positional index. Tag your own with a `CLAUDE:` text prefix and delete them
  highest-index first. In live mode, re-run `notes.list` and match the prefix right before each delete: a human edit
  can shift the indices. `notes.add` dirties the document and adds a history step. Notes survive PSD and `.pcraft`.
- **Actions** (`actions.record {"name":...}`, `actions.stop`, `actions.get {"action":...}`) capture every try,
  including undo/redo with params. Recording does not dirty the document. Headless actions last only for the
  session; remove one with `actions.delete {"action":name}`.

## Live mode (the open app window)
The live-GUI details below were not re-checked on 0.6.0 (only the headless parts were); treat them as best effort.
Start the GUI with `--control <port> --control-token-file F` and the same automation roots, **with its working
directory set to the automation root**, then connect `photocraft-cli mcp --bridge 127.0.0.1:<port>
--control-token-file F`. `ui_*` and `control_call` work only in this mode.
- **Token file:** plain ASCII/UTF-8 **without a BOM**. In Windows PowerShell 5.1 use `Set-Content` or
  `Out-File -Encoding ascii`; `-Encoding utf8` adds a BOM and the default is UTF-16, and the GUI then exits 2 with
  the reason only on stderr. The port is 127.0.0.1-only and needs the token as the first request; keep it on loopback.
- **State:** `session_list` returns the `ui.inspect` payload: `session.documents[*].{index,path,name,revision,dirty}`,
  `session.active`, and the active document's full inspect under `document`. `doc_inspect {"index":n}` reads a
  non-active document without switching to it.
- **Edits act on the ACTIVE document.** Most commands ignore a `document` param silently. For safe work,
  `image.duplicate` the user's document and re-check `session.active` right before each step: a click in the
  window can switch tabs under you.
- **Never close the user's documents.** `doc_close` and `doc_select` are headless-only (live mode not re-checked).
  `file.close` / `file.closeAll` through `control_call` or `command_run` **discard unsaved changes silently**
  (verified headless; live not re-checked). Check `dirty` first and close only documents you created.
- **Screenshots:** bridge `doc_render_preview` is a window capture that raises and focuses PhotoCraft. For a
  read-only capture that does not steal focus use `control_call {"method":"ui.screenshot","params":{"focus":false}}`
  (base64 PNG in `json.base64`).
- **Keys:** on Windows, Ctrl shortcuts need `command:true` (Ctrl+Z = `{"key":"Z","command":true}`); `ctrl:true`
  returns ok but does nothing. A synthetic Ctrl+S does not save.
- **Dialogs:** `ui_menu_invoke` of a dialog command returns `{dialog:id}`; drive it with `ui.dialog.set` and
  `ui.dialog.confirm`. Engine commands still run under open dialogs, and an open Image Size dialog re-applies its
  old size if you resize underneath it, so cancel any dialog listed in `ui.inspect.dialogs` before editing. The
  Unsaved-changes prompt is not listed there; only `ui.key` Escape/N/Y answers it.
- **Saving:** `doc_open` of an already open file opens a second copy. Saves never check for external changes (last
  writer wins). A file opened through automation and saved with Ctrl+S is written relative to the GUI's working
  directory (hence the cwd rule above). A human save shows as `dirty` going true → false; confirm the file's mtime.
- **Connections:** idle control and bridge connections close after 30 s.

### Watching what the user does (observation recipe, not re-checked)
Read-only. In our scripted live-mode trials this detected every edit we made; treat it as best effort. Watching what
a person does needs their consent, so tell them it is happening.
1. At start, `actions.record {"name":"CLAUDE observe <ts>"}` (does not dirty the document or move the revision).
2. Every ~1 s, `session_list`: compare each document's `revision` and `dirty`, and keep the tool, brush, zoom,
   dialogs and status as context (tool switches never reach the journal).
3. On a revision change, `doc_inspect {"index":n}` and diff it with the previous dump, keyed by `path` + layer
   `id`: visibility, opacity, blend, mask, name, bounds, size, selection, notes and new history labels.
4. Read the journal: while recording, `actions.get` shows 0 steps until a no-op
   `actions.move {"action":name,"step":0,"to":0}` publishes the pending steps. Steps carry filter params, every try
   (e.g. blur 12 → undo → blur 3) and `paint.stroke` points with `target:"pixels"|"mask"` (no size or colour).
   A quick edit + Ctrl+Z inside one tick is visible **only** in the journal.
5. Never call `doc_save`/`doc_export` on the user's documents. At the end, `actions.stop` and
   `actions.delete {"action":name}` (otherwise it persists in the Actions panel), and check the user's saved file
   in a separate headless `photocraft-cli mcp`. Pointing with `notes.add` dirties their document; skip it after
   they have saved.

## Without MCP
`photocraft-cli` also has a headless CLI. Tested: `photocraft-cli convert in.png out.psd` and
`photocraft-cli info file --compact`. It has more subcommands (single-command runs, batch, droplets); check
`photocraft-cli --help` before you rely on one.
