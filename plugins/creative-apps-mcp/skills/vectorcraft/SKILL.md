---
name: vectorcraft
description: Unofficial third-party skill. Drive VectorCraft (open-source Illustrator-style vector editor) through its MCP server — draw shapes, paths and text, apply paint/effects/pathfinder, and export SVG/PDF/PNG/EPS/DXF/AI files, headless or in the live app window, including watching what a human changes in the live window. Use when the user wants vector artwork, icons, logos, posters or SVG/PDF exports made or edited with VectorCraft.
---

# VectorCraft via MCP

Server: `vectorcraft`. This plugin starts it as `vectorcraft-cli mcp --headless`. Tested on Windows 11 with
0.8.0 (earlier 0.6.0/0.7.0 runs not re-checked). A headless server starts in milliseconds and renders on the
CPU, so a fresh process per job is cheap.

- **Always pass a mode.** A bare `vectorcraft-cli mcp` attaches to anything listening on `127.0.0.1:7979`, and
  DesignCraft's live app also uses that port by default. Observed once (not re-checked): it drove that app as if
  it were VectorCraft (its `undo` undid a DesignCraft edit). With nothing listening, it falls back to headless;
  the only sign is a `headless` line on stderr and in the server instructions, with no fallback warning. Use
  `--headless`, or `--connect 127.0.0.1:<port>` for a live window (see below).
- `--automation-read-root` / `--automation-write-root` are rejected on 0.8.0 ("unknown mcp option").

## Start with a health check
Before you do any work, call `inspect_document {"depth":0}`. You should get artboards, layers, revision and
history. In a live session, also run the identity check under **Live app**.

## Tested workflow
1. Make sure a document exists:
   - **Headless** starts with one (612×792).
   - **Live app** may start with none. Call `run_command {"command":"file.new","params":{"name":"Poster","backgroundContents":"white"}}`
     (the key is `command`, not `id`). It runs without a dialog. Presets come from `file.newPresets`.
2. `draw_shape {"shape":"rectangle","x":50,"y":50,"width":400,"height":250,"radius":24,"fill":"#ff6633"}`
   returns `{id}`. The other shapes and their parameters (`rect` and `circle` are accepted as aliases):
   - `ellipse`: x, y, width, height
   - `polygon`: cx, cy, radius, sides
   - `star`: cx, cy, radius1, radius2, points
   - `line`: x1, y1, x2, y2
3. `add_text {"text":"Hello","x":80,"y":180,"color":"#ffffff"}`. Always pass `color` (see Traps). Add
   `width`/`height` for area type, or pass `path` + `mode` to set type on a path.
4. **Read back** what you changed: `run_command {"command":"document.node","params":{"id":N,"summary":true}}`
   returns bounds, fill hex, kind and anchors.
5. **Look at it:** `screenshot` returns a PNG of the artboard. Open the image before you say what it shows.
6. `export {"path":"/abs/out.svg"}`. The format comes from the extension or from `format`: vectorcraft, svg,
   svgz, pdf, ai, png, png8, jpg, gif, webp, tiff, bmp, tga, psd, eps, dxf, emf, wmf, txt or template. Pass
   format options through `options` (`run_command document.formats` lists them). Omit `path` to get base64 back.
7. `save_file {"path":"/abs/out.vectorcraft"}` saves the native file (also .svg, .pdf, .ai or .vctemplate).
8. Several commands at once:
   - `command_batch {"steps":[{"id":"…","params":{…}}, …]}` adds one undo step per step. It returns
     `{completed, failed, results}`, stops at the first error unless you pass `"stop_on_error":false`, and on
     failure it sets isError. Exactly `completed` undos restore the earlier state.
   - `run_command {"command":"command.batch","params":{"label":"…","commands":[{"command":"…","params":{…}}]}}`
     is ONE undo step, and it rolls everything back if any command fails.

## Traps (verified on 0.8.0): a reply of "ok" is not proof
- **Most commands don't check their params** (a few, such as `select.set` and `document.find`, do). Top-level
  tool arguments are strict: an unknown key gives error -32602, which names the key. But the `params` inside
  `run_command`, `command_run` and `command_batch` mostly are not validated:
  - Unknown or misspelled keys are usually ignored.
  - A missing number, or a number sent as a string, often becomes 0 or the dialog default (for example
    `object.move {}` or `object.rotate {"angle":"30"}`).
  - The reply is still ok, and an undo step is still pushed.

  Read the object back after every `run_command`.
- **Numbers must be JSON numbers.** `transform {"dx":"10"}` replies `applied:["move"]` and moves nothing (a
  string `rotate` or `scale` does raise an error). For `draw_shape`, `sides` and `points` must be integers:
  `4.4` or `"8"` silently gives the defaults (6 sides, 5 points), and `points:2` is accepted.
- **Colours:** `[r,g,b]` values must be 0..1. Larger values are clamped per channel without an error, while
  the reply echoes your input (`[255,128,0]` becomes `#ffff00`). These forms work: `#rgb`, `#rrggbb`, CSS
  names such as `red`, CMYK `{c,m,y,k}`, `{gray}`, `"none"`, `{"gradient":…}` and `{"swatch":name}`.
  `#rrggbbaa` drops the alpha without telling you.
- **`set_paint {ids}` doesn't check that the ids exist.** `[999]`, `["2"]` and `[]` all reply "applied" but
  change only the default paint. A negative `strokeWidth` is stored as 0, but the reply echoes your value. Read
  the paint back. (`transform` and `select.set` do reject bad ids.)
- **The default paint drifts.** `set_paint`, and `draw_shape` or `draw_path` given a paint, also change the
  paint used for new art, and undo does not change it back. `add_text` without `color` then uses that fill.
  New shapes start with a 1 pt black stroke; remove or change it with `set_paint`.
- **`text.editRange` needs both `start` and `end`** (byte offsets):
  `{"id":T,"start":0,"end":6,"insert":"XX"}`. With `{id}` alone it erases the whole text, and with
  `{id, insert}` it replaces all of it.
- **Fonts:** if the font family isn't installed, `add_text` still succeeds and renders in Source Sans 3. Check
  `run_command text.fonts` for status `missing`. Unicode (accents, CJK, emoji) round-trips. U+2028 and U+2029
  render as a missing-glyph box, so use `\n` for line breaks. CJK and emoji rendered through system font fallback
  on the test machine and may differ elsewhere.
- **Ids:**
  - Ids are sequential, and undoing a creation rewinds the counter, so the next new object reuses the undone
    id. Never hold an id across an undo; find it again with `document.find`.
  - Ids freed by a delete are not reused.
  - Ids survive save and reopen for .vectorcraft, .ai and .pdf. An SVG reopen renumbers them.
- **Names:** swatch, graphic style, symbol, character and paragraph style, brush, saved-selection, effect and
  tool names are exact and case-sensitive; a prefix gives an error. `document.find {"name":…}` is a
  case-insensitive *substring* match (`Logo` also matches `Logo copy`). `{"kind":…}` is an exact,
  case-insensitive label, and stars report `Path`.
- **Saving and exporting overwrite existing files without telling you.** Use a new path for each output.
  - Windows-only: names containing `| ? * < > "` fail with os error 123.
  - Windows-only: reserved names with an extension (`NUL.svg`, `CON.svg`) are accepted and create a file Explorer
    cannot easily delete. A bare `NUL` fails with an OS error. Sanitize file names yourself.
  - `export` to a path with no extension writes PNG, and so does a trailing-dot path (`x.svg.` writes PNG bytes
    to `x.svg`). `save_file` writes the native .vectorcraft format there instead. Unknown extensions error.

## Reading the document
- **`inspect_document`:** `{"depth":0}` returns the layer skeleton plus up to 500 history labels (about 10 KB).
  Locate objects with `run_command document.find`, which accepts `name`, `kind`, `text` and `limit`.
- **`document.node`:**
  - `{id}` returns the full model: `appearance.items[].paint.color` as 0..1 floats, `appearance.effects`,
    `kind.live` and `kind.path`.
  - `{id, summary:true}` returns the short summary. `depth` and `childLimit` are errors unless `summary:true`
    is also passed.
- **Live effects** (`apply_effect`) don't show in `inspect_document` or in the summary. Read them with the full
  `document.node` or with `run_command effect.list {"ids":[N]}`.
- **Fingerprint:** `run_command document.json` gives the complete model, and it is deterministic across reads
  and fresh opens.
- **Undo steps:**
  - `draw_shape` with a fill pushes 2 (the shape plus "Fill Color"), and `stroke` or `strokeWidth` add one each.
  - `add_text` with a colour pushes 1.
  - `transform` pushes one per operation.
  - Many no-op edits still push a step.

## Interchange
- **PDF, AI and EPS embed the native document by default** (PDF `preserveEditing` defaults to true). A
  VectorCraft reopen is lossless, but it only proves a self round-trip.
- **To test real interchange,** export with `"options":{"preserveEditing":false}` and read the file with an
  independent tool (PyMuPDF and pdftotext work). Such a PDF keeps text as text, gradient stops and clip groups,
  but flattens symbols to paths.
- **`.ai` is a PDF-compatible container** (it starts with `%PDF-1.7`). Opening it in Adobe Illustrator was not
  checked.
- **SVG export** writes real `<text>`, `linearGradient` and `clipPath`. Symbol instances are written as expanded
  groups, with no `<symbol>`/`<use>` (0.8.0). An SVG reopen keeps every object, but live shapes become `Path` and
  ids are renumbered. `save_file` to .svg warns about format loss; `export` to .svg does not.
- **`vectorcraft-cli convert IN OUT`** gives bytes identical to the MCP `export` for every format except PDF, AI
  and EPS, which differ only in embedded dates and IDs.

## Live app (`vectorcraft --control <port>`)
Observed once on Windows 11 with 0.8.0; not re-checked, since it needs the GUI.
1. **Launch** the app with `vectorcraft --control 7979` and record its PID. Then check that netstat's LISTEN row
   on the port belongs to that PID (Windows). If the port was already taken, a second instance runs with NO control
   server, and the only sign is `os error 10048` on stderr.
2. **Connect** with a separate server: `vectorcraft-cli mcp --connect 127.0.0.1:7979`. `--connect` doesn't verify
   which app it reached. Its first call, `inspect_ui`, must contain `graphicsAdapter` and `screenMode`. DesignCraft
   returns `currentPage` instead, so refuse to continue if they are missing. If nothing is listening, `--connect`
   exits within about a second, and the client sees only a dead server.
3. **Native modals block everything.** Never call `file.save`/`file.saveAs`, or `save_file` on an untitled
   document, without a path. That opens a native Save As dialog that blocks every control connection, and the
   bridge can't see it or dismiss it. Calls then time out after 60 s.
4. **A call that timed out may still run later.** Inspect the document before you retry anything that edits it.
5. **`file.close` on a dirty document** returns `{pending:"saveChanges"}`. Headless has no dialog: there it
   closes the document with no prompt, so save first.
   - To discard (unsaved changes are lost): `ui.dialog.set {"field":"discard","value":true}`, then
     `ui.dialog.confirm`.
   - To keep the document: `ui.dialog.cancel`.
   - The dialog's `fields.index` names the tab it will close.
6. **Opening a path that is already open** creates a second tab with the same title, and saves from the two tabs
   overwrite each other. Check `inspect_ui` `documents[].title` first, and use `document.activate {index}`.
7. **`pointer_gesture`:**
   `{"tool":"rectangle","events":[{"kind":"down","x":300,"y":100},{"kind":"drag","x":400,"y":200},{"kind":"up","x":400,"y":200}]}`.
   The size comes from the last `drag`, not the `up`, so end with a drag to the final point and an up at the
   same point. A down and up with no drag is a click, which opens the tool's size dialog. UI replies can return
   before the edit shows, so poll again rather than asserting at once.
8. **Port limits:** the control port binds to 127.0.0.1 only and accepts at most 16 connections. When it is
   full, an MCP server still initializes but fails on its first tool call. Keep it on loopback: anything that
   can connect can drive the app.
9. **Stop the app** (Windows: `Stop-Process -Id <pid>`), which closes the port at once. Stop only an instance you
   launched. Unsaved work in it is lost.
10. **Exports match.** SVG and PNG exports are byte-identical between the GUI bridge, headless and `convert`.
    PDFs differ only in their creation and modification dates, XMP dates and `/ID`.

### Watching a human edit the live window (one run: 26/26 edit types caught within one 1 s poll, not a guarantee)
Watching what a person does needs their consent. Tell them it is happening before you start.
1. **Connect** with an explicit `--connect` and run the identity check above.
2. **Poll** `inspect_document {"depth":0}` every second. Use a change in `revision` only as the trigger:
   - The revision also rises on selection-only changes.
   - Undo shrinks the history and grows the redo list.
   - Text typed in the window changes content before "Typing" enters the history (it commits on Escape).
3. **Re-baseline instead of diffing** whenever any of these change: path, title, `activeDocument` or the number
   of documents. Opening a file starts a new tab whose revision restarts at 1. Also re-baseline when the history
   is cleared together with a content change (`file.revert`).
4. **Dump on each trigger:**
   - **Full dump:** `inspect_document {}` plus `run_command document.json` (one live run: about 66 KB and 0.3 s for 14
     objects; headless measured about 50 KB).
   - **Sliced dump, for large documents:** `inspect_document {"depth":1}`, `document.node {summary:true}` for
     each container whose summary changed, the full `document.node` of the selection, and `run_command
     swatch.list`. The swatch list is needed because a global swatch edit doesn't show in the summaries.
5. **Decide whether anything changed** with a hash of the content. Diff by object id. Treat the same id with a
   different kind as a remove plus an add, because ids are reused after undo. If the history grew but the hash
   is equal, fetch the selection's full node: an effect parameter edit shows only there.
6. **Leave notes for the human:**
   1. `run_command layer.new {"name":"CLAUDE","top":true}`.
   2. `add_text` with an explicit `color`.
   3. `object.setProps {"id":N,"name":"CLAUDE: <tag>"}`.
   4. Restore the human's layer with `layer.setCurrent` and their selection with `select.set`.

   Each note adds history entries to the human's undo stack and marks the document dirty.
   `layer.delete {"id":L}` removes all notes in one undoable step. `layer.setProps {"id":L,"template":true}`
   keeps the notes out of PNG exports.
7. **Analyse without touching the human's file:** `export {"format":"vectorcraft","path":"<copy>"}` writes a
   native copy, and the live document keeps its path, title and dirty flag. Open the copy in a separate
   `vectorcraft-cli mcp --headless` and export SVG or PNG from there.

## Notes
- **Transparent background:** a PNG export of an artboard with no background is RGBA with a transparent
  background. Don't mistake it for black when you check the export.
- **All commands:** `list_commands` lists every command; run any of them with `run_command`.
- **Built-in prompts:** `poster`, `icon-set`, `recolor`, `trace-and-style` and `export-set`.
- **GPU:** on machines with two GPUs, the 0.6/0.7 GUI may render on the integrated GPU (storytold/vectorcraft#849).
  On the test machine, the 0.8.0 GUI reported the discrete GPU in `inspect_ui` `graphicsAdapter`.
