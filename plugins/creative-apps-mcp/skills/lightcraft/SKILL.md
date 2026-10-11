---
name: lightcraft
description: Unofficial third-party skill. Drive LightCraft (open-source Lightroom-style photo library and raw developer) through its MCP server — import photos/raws, set develop sliders, LUT profiles, presets, crop, virtual copies, ratings and keywords, render previews and export JPEG/PNG/TIFF/WebP/AVIF/DNG; or connect to the live LightCraft window to assist or observe a person's edits. Use when the user wants to grade, develop, cull, rate, query or batch-export photos with LightCraft, or watch what they do in it.
---

# LightCraft via MCP

Server: `lightcraft`, launched by this plugin as `lightcraft-cli mcp --compact`. Tested with 0.5.0 on Windows 11.

- **Compact mode** lists **17 tools** (about 16 KB): the helpers `list_commands`, `run_command`, `import`,
  `query_photos`, `select_photos`, `list_controls`, `get_develop`, `set_develop`, `apply_preset`, `crop`,
  `render_photo`, `export`, plus the shared core tools `command_list`, `command_run`, `command_batch`,
  `doc_inspect`, `render_preview`. Without `--compact` it lists **300 tools** (about 146 KB), one per engine command.
  Every engine command is reachable through `run_command {"command": id, "params": {...}}`; `list_commands`
  gives the ids and their parameter docs.
- **Headless library:** in-memory by default. `--library DIR` makes it persistent, `--demo` loads a procedural
  demo library.
- **Flags:** unknown `--` options are rejected (exit 1, `unknown option` on stderr). `mcp --help` is rejected too;
  use `lightcraft-cli --help`. A single-dash word such as `-h` is treated as a file path to import. stdout carries
  only JSON-RPC, even with `RUST_LOG=debug`.

## How to work
1. **Health check first:** one `query_photos {}` (or `doc_inspect`) call. In live mode also check
   `ui_inspect` for `libraryProblem` (see Live mode).
2. **Read back after every edit.** An ok reply is not proof: several inputs are silently clamped, refitted or
   ignored (see Traps). Use `get_develop`, `query_photos` / `catalog.query` and `photo.inspect`.
3. **Look at renders.** `render_photo {"size":1024}` returns the developed image; open it before you
   export or report. After exporting, check the file itself (size, dimensions, colour).

## Tested workflow (headless)
1. `import {"paths":["/abs/photo.jpg"]}` → `{"imported":[1]}`. Folders are scanned recursively.
   `mode: copy|move` with `destination` copies or moves the files in, into `destination/YYYY/YYYY-MM-DD/` unless
   `organize:"flat"`; the default `add` references them in place. **`move` removes the originals from the source
   (their XMP sidecars go too):** use `copy` unless the user asked for a move.
   - Results are in the payload, and `isError` stays false: `duplicates[]` (reason `path` or `content`) and
     `failed[]` (with a reason). Read both.
   - Folder scans silently skip files without an image extension; a file named explicitly is content-sniffed.
   - EXIF orientation is applied on render and export; exports are written with orientation 1. Unicode, CJK and
     emoji file names round-trip.
2. `list_controls` gives develop control ids and ranges, e.g. `light.exposure`, `light.contrast`.
3. `set_develop {"values":{"light.exposure":0.7,"light.contrast":25}}`. Each call is one undo step.
4. `render_photo {"size":1024}` and look at it.
5. `export {"path":"/abs/out.jpg","longEdge":0}` for one photo, or `{"dir":"/abs/outdir"}` for a batch.
   - **Without a size parameter the long edge is 3000 px** for MCP `export` and `app.export`; it never enlarges
     (`dontEnlarge` defaults true). `lightcraft-cli render` defaults to full size. `longEdge: 0` keeps full size;
     `shortEdge`, `percent` etc. also work.
   - Other options: `colorSpace` (srgb, displayP3, adobeRgb, proPhoto, rec2020; the ICC tags are correct),
     `bitDepth`, `format`, `quality`. DNG export needs a raw photo (errors on a JPEG); raw handling not re-checked.
   - JPEG quality defaults to 90 for MCP `export` and `app.export`, but 92 for `lightcraft-cli render`.
     8-bit PNG exports are RGBA with opaque alpha; 16-bit PNG is RGB.

### More recipes that were run
- **Query:** `query_photos {"filter":{"rating":3,"ratingOp":"atLeast"}}` (`ratingOp`: `atLeast`, `exactly`,
  `atMost`). Recognised filter keys include `text, rating, ratingOp, flag, label, kind, keyword` (a parent keyword
  matches its children), `edited, date, camera, person, merged, libraryFolder`,
  `album, dateFrom, dateTo, deleted, folder, imported, importedFrom, lens, subfolders`. Wrong-typed values are
  errors (`merged` takes a string).
- **Virtual copy (the agent's duplicate):** `run_command photo.virtualCopy {"ids":[1],"name":"v2"}` →
  `{"ids":[new]}`. The copy shows `copyOf` and `copyName` in `query_photos`, shares `source.path`, and its edits
  and undos never touch the master.
- **LUTs:** `run_command profile.import {"paths":["/abs/look.cube"]}` → ids like `lut:imported-<slug>`. The slug
  comes from the .cube `TITLE` line if present, else the file name; take the id from the reply (a re-import adds
  `-2`). Apply with `run_command develop.profile {"id":"<id from the reply>","amount":100}` (amount 0..200,
  out-of-range values are clamped); restore the default with `{"id":"lc.color","amount":100}` (the old amount
  otherwise stays). Imported LUTs are missing from `profiles.list` (storytold/lightcraft#618) but
  appear in `profiles.menu`. The LUT is applied to sRGB-encoded values and amount extrapolates linearly in that
  space (200 doubles the change until 8-bit clipping).
- **Export preset:** `run_command export.savePreset {"name":"web","params":{...app.export params...}}`. Pass
  `params` explicitly: headless and CLI never have a "last export" to save.
- **History:** `run_command journal.list {"limit":N}` returns the newest N entries in oldest-first order, as
  `{command, params}` with no timestamp, for the current session only (empty after a reopen). Failed commands
  are not journaled; successful no-op edits are. Helper tools with a singular `id` add a `library.select` entry
  first; commands taking `ids` carry the ids in params and add none. `history.list` returns
  `{history:[labels], versions}` for the active photo.
- **Persistence:** a `--library` survives a hard process kill (tested on Windows; power loss untested). After
  the kill the stale `catalog.lock` is handled on reopen and every acknowledged change is present.
- **CLI equivalents:** `lightcraft-cli render in.raw -o out.jpg --set light.exposure=0.5`,
  `lightcraft-cli merge hdr|panorama`, and `lightcraft-cli run --library DIR <command> ...`.

## Traps
- **`query_photos` ignores unknown filter keys** and returns every photo. `{"minRating":3}` does nothing; use
  `rating` + `ratingOp`. Always check `total` in the reply.
- **`export {path}` always overwrites** an existing file, whatever `conflict` says, and the reply doesn't say
  so. `conflict` (`unique`/`skip`) only applies to `{dir}` exports (a second run writes `name-2.jpg`). Check
  the target before exporting to a path. Writing over a library original is refused.
- **Export reply paths echo the input.** A relative path resolves against the server's (or CLI's) working
  directory and comes back relative; dir exports return `dir/name` with a forward slash (mixed separators for
  an absolute Windows dir). Pass absolute paths and normalise before comparing.
- **Headless export blocks** and ignores `background:true`. With `_meta.progressToken` you get
  "Exporting X (k of N)" notifications. `ping` is answered between photos (busy, not hung); other requests
  queue until the export ends.
- **`set_develop {values}` clamps** out-of-range numbers to the control's range (exposure 1e9 becomes 5.0) and
  reports the clamped value in `controls[].value`; compare it with what you sent. Unknown ids, strings and null
  are errors. **`set_develop {settings}`** (a partial develop-settings JSON, the shape `get_develop` returns)
  replies `controls: []` even when it worked, ignores unknown keys silently and does not clamp (exposure 99 was
  stored). Read back `get_develop`.
- **`crop` refits silently:** rects outside 0..1 are refitted, inverted rects swapped, the angle clamped to ±45;
  a non-numeric angle is ignored but still adds an undo step. Read back `get_develop` → `crop.geometry`.
- **Exported XMP:** rendered JPEGs carry `xmp:Rating` and `dc:subject` but not the colour label or pick flag,
  even with `metadata:"all"`. In 0.5.0 hierarchical keywords are written as literal `a|b|c`. Use
  `format:"original"` when the label or flag must travel: that sidecar carries `xmp:Label` and `lc:flag`.
- **Dates:** headless imports and edits are stamped 2026-09-30T12:00:00 (storytold/lightcraft#554).

## Live mode (the user's open window)
Not re-checked on 0.5.0 (needs the GUI): treat everything under this heading as unverified.
- **Launch:** `lightcraft --library <lib> --no-demo --control 7980`; the port is up in about 3 s. Register a second
  server with `lightcraft-cli mcp --connect 127.0.0.1:7980 --compact` (27 tools, adding `ui_inspect`,
  `ui_screenshot`, `screenshot`, `inspect_ui`, `set_ui`, `list_widgets`, `click`, `press_key`, `type_text`,
  `pointer_gesture`). The port has no auth: keep it on loopback. Close the app when done only if you launched it
  (unsaved work is lost). On Windows the GUI rewrites `%APPDATA%\LightCraft\ui.json`, so back it
  up if you launch it for tests.
- **Before any write:** check `ui_inspect` → `libraryProblem`. While it is set, reads return an empty library and
  writes go into a throwaway session that is lost on Try Again (ids get reused).
- **Writes that leave the person's active photo alone:** `run_command` with `ids` for `photo.rate`,
  `photo.label`, `photo.setMeta`, `develop.set {ids, values}`, `app.export {ids}`, and `apply_preset {ids}`.
  `set_develop {id}`, `crop {id}`, `export {id}` and `photo.virtualCopy` move their active photo and selection.
  Reads (`get_develop`, `render_photo`, `render_preview`, `photo.inspect`) don't. Measured headless only; the tool
  schemas say "Makes that photo active first".
- **One shared undo stack:** never call `edit.undo` in a live session; the person's Ctrl+Z undoes your last step.
- **Listing photos:** `catalog.query {"filter":{}}` lists all photos; `query_photos` without a filter returns only
  the person's current view. A photo's path is `photo.inspect` → `source.path` (catalog rows carry `fileName`).
- **Don't probe:** a failing command's error text appears in the person's status bar.
- **Keywords you add** go into their reserved "Recent Keywords" set and stay there after `keyword.delete`;
  Alt+1..9 re-applies them. Warn the user before tagging.
- **Dialogs:** no MCP tool closes one; `ui.dialog.cancel` replies ok even when nothing is open. Use
  `click {"widget":"button:dialogCancel"}` or `press_key` Escape. In-app dialogs show only in the widget list
  (`dialog:window`); native file dialogs show in `ui_inspect` → `fileDialogs` but not in screenshots. Bridge
  writes still run behind modals. Don't press OK in the Export dialog; use `app.export` with an explicit path.
- **Render barrier:** `ui_screenshot` waits for finished renders (about 155 ms after an edit).
- **Analysing their library:** copy the library folder without `catalog.lock` and `catalog.lock.owner`, then
  `lightcraft-cli run --library <copy> ...`. Never open the live library from a second process
  (storytold/lightcraft#579).

### UI input (only when a command won't do)
- Widget ids: `thumb:<id>` (grid), `film:<id>` (filmstrip), `slider:<controlId>`, `sliderValue:<controlId>`,
  `cropHandle:0..7` (0 = top-left), `preset:<presetId>`, `icon:edit|crop|keywords|presets` (these toggle; check
  `ui_inspect` → `ui.right` / `ui.presets` first), `star:bottom:N`, `flag:pick`, `flag:reject`, `field:keyword`,
  `dialog:window`, `button:dialogOk`, `button:dialogCancel`, `button:libraryRetry`, `button:libraryTemporary`.
- Clicks hit the rect centre even when another panel covers it (a `film:<id>` under the Presets panel applied a
  preset). Close overlapping panels first.
- Never type slider values with double-click + Ctrl+A: if the field doesn't take focus, Ctrl+A selects every
  photo and the next keys edit them all. Use `develop.set` or a slider drag (about 0.9 contrast per px).
- Crop-corner drags need steps of 3 px or less; coarse steps grab the move handle.
- Hotkeys: 1-5 rating, p pick, x reject (in the Crop panel x is Swap Aspect and fires twice, so it does nothing),
  u unflag, 6 red label, Ctrl+' virtual copy, Ctrl+Z undo.

### Observing what the person does (one run, Windows 11: 18 of 19 scripted actions detected, 0 errors)
Observe only with the person's explicit consent: they must know it is happening and what is recorded.
One `--connect ... --compact` session, everything through `run_command` and `ui_inspect`:
1. **Tick every 2 s:** `journal.list {"limit":1}`, `library.info` → `persistence.appends` (one increment per
   committed step) and `library.state` undo/redo labels. Entries have no id or time, so `limit:1` alone misses
   repeats.
2. **On a change:** read the journal by cursor (`journal.list {"limit": cursor+256}`, then `result[cursor:]`;
   exact, as it is append-only within a session); `history.list` for the active photo; `catalog.query
   {"filter":{}}` diffed by id + path; and a leaf diff of `get_develop` for the touched photos (ids in params,
   `library.select` targets, the active photo before and after; diff a new copy against its master).
3. **Attribution:** entries for selection-relative commands carry no photo id; replay the `library.select`
   entries (thumbnail and filmstrip clicks are journaled as `library.select`).
4. **What the journal shows:** slider drags as `develop.beginInteraction`, each `develop.set`, then
   `develop.endInteraction`; hotkeys as `photo.rate` / `photo.pick` / `photo.label`; keywords as
   `photo.setMeta addKeywords`; crop drags as `crop.drag`; presets as `preset.apply {id, amount}`; `edit.undo`.
5. **Exports are not journaled.** Background exports (the Export dialog) set `ui_inspect` → `export.last` (no
   timestamp); a synchronous `app.export` over the control channel leaves no trace.
6. **Attention:** one `ui_inspect` per tick gives dwell time per photo and view.
