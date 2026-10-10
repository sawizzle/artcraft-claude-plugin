---
name: vectorcraft
description: Drive VectorCraft (open-source Illustrator-style vector editor) through its MCP server — draw shapes, paths and text, apply paint/effects/pathfinder, and export SVG/PDF/PNG/EPS/DXF/AI-compatible files, headless or in the live app window. Use when the user wants vector artwork, icons, logos, posters or SVG/PDF exports made or edited with VectorCraft.
---

# VectorCraft via MCP

Server: `vectorcraft`. This plugin starts it as `vectorcraft-cli mcp --headless`. Tested on Windows 11 with 0.6.0 and
0.7.0. Without `--headless`, the server attaches to anything listening on `127.0.0.1:7979` (where
`vectorcraft --control 7979` listens, and also DesignCraft's default port), and otherwise runs headless.
For a live window, register a separate server with `--connect 127.0.0.1:7979`.

## Tested workflow
1. Make sure a document exists:
   - **Headless** starts with one.
   - **Live app** starts with none. Call `run_command {"command":"file.new","params":{"name":"Poster","backgroundContents":"white"}}`.
     Note the key is `command`, not `id`. Presets come from `file.newPresets`.
2. `draw_shape {"shape":"rectangle","x":50,"y":50,"width":400,"height":250,"radius":24,"fill":"#ff6633"}`
   → `{id}`. The available shapes and their parameters:
   - `ellipse`: x, y, width, height
   - `polygon`: cx, cy, radius, sides
   - `star`: cx, cy, radius1, radius2, points
   - `line`: x1, y1, x2, y2
3. `add_text {"text":"Hello","x":80,"y":180,"color":"#ffffff"}`. Add `width`/`height` for area type, or
   pass `path` + `mode` to set type on a path.
4. `screenshot` returns a PNG of the artboard. Look at it.
5. `export {"path":"/abs/out.svg"}`. The format comes from the extension:
   svg/svgz/pdf/png/jpg/webp/gif/tiff/bmp/eps/dxf/emf/wmf/tga/psd. Omit `path` to get base64 back.
6. `save_file {"path":"/abs/out.vectorcraft"}` saves the native file (or .svg/.pdf/.ai/.vctemplate).

## Notes
- **Paint values:** `fill` accepts `"#rrggbb"`, `[r,g,b]` with values 0..1, CMYK `{c,m,y,k}`, `{gray}`,
  `"none"`, or a full paint object (`{"gradient":…}`, `{"swatch":name}`).
- **Default stroke:** new shapes get a 1 pt black stroke. Use `set_paint` to remove or change it.
- **Transparent background:** a PNG export of an artboard with no background is RGBA with a transparent
  background. Don't mistake it for black when you check the export.
- **Large documents:** call `inspect_document {"depth":0}` first. After that, find nodes with
  `run_command document.find` and read them with `document.node`.
- **All commands:** `list_commands` lists every command; run any of them through `run_command`.
- **Built-in prompts:** the server also exposes the prompts `poster`, `icon-set`, `recolor`,
  `trace-and-style` and `export-set`.
- **GPU:** on machines with two GPUs, the 0.6/0.7 GUI may render on the integrated one (power preference
  LowPower). This is fixed on main after 0.7.0 (storytold/vectorcraft#849).
