---
name: lightcraft
description: Drive LightCraft (open-source Lightroom-style photo library and raw developer) through its MCP server — import photos/raws, set develop sliders, presets, crop, render previews, and export JPEG/PNG/TIFF/WebP/AVIF/DNG. Use when the user wants to grade, develop, cull, rate or batch-export photos with LightCraft.
---

# LightCraft via MCP

Server: `lightcraft`, launched by this plugin as `lightcraft-cli mcp --compact`. Tested with 0.4.0 on Windows 11.

- **Compact mode:** without `--compact` the server lists **252 tools**, one per engine command. Compact
  lists 12 helpers, and every engine command stays reachable through
  `run_command {"command": id, "params": {...}}`. Use `list_commands` to find ids.
- **Headless library:** by default the server keeps an in-memory library. Pass `--library DIR` for a
  persistent one, or `--demo` for a procedural demo library.
- **Live mode:** start the app with `lightcraft --control 7980` and the server with
  `--connect 127.0.0.1:7980`.

## Tested workflow
1. `import {"paths":["/abs/photo.jpg"]}` → `{"imported":[1]}`. Folders are scanned recursively.
   `mode: copy|move` with `destination` copies or moves the files in; the default `add` references them
   in place.
2. `list_controls` gives develop control ids and their ranges, e.g. `light.exposure`, `light.contrast`.
3. `set_develop {"values":{"light.exposure":0.7,"light.contrast":25}}`. Each call is one undo step.
   `settings` takes a partial DevelopSettings JSON instead (the shape `get_develop` returns).
4. `render_photo {"size":1024}` returns the developed image. Look at it.
5. `export {"path":"/abs/out.jpg","longEdge":0}` exports one photo, or `{"dir":"/abs/outdir"}` exports in batch.
   - **Without a size parameter, exports are resized to a 3000 px long edge.** `longEdge: 0` keeps full
     size. You can also set `longEdge`, `shortEdge` or `percent`.
   - Other options: `colorSpace` (srgb, displayP3, adobeRgb, proPhoto, rec2020), `bitDepth`, `format`,
     `quality`.

## Notes
- **Other helper tools:** `query_photos {"filter":{"minRating":3}}`, `select_photos`, `apply_preset`, `crop`.
- **Known upstream bugs:**
  - storytold/lightcraft#554: headless imports and edits are stamped with a fixed test date.
  - storytold/lightcraft#579: a persistent library can't be opened while another process holds it.
- **CLI equivalents:** `lightcraft-cli render in.raw -o out.jpg --set light.exposure=0.5` and
  `lightcraft-cli merge hdr|panorama`.
