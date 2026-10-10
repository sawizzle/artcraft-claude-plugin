---
name: effectcraft
description: Drive EffectCraft (open-source After Effects-style motion graphics/VFX app) through its MCP server — create comps, solids/text/shape layers, effects, keyframes and expressions, run After Effects-style JavaScript, render frames, and render H.264/HEVC/ProRes/WebM/EXR via the render queue. Use when the user wants motion graphics, titles, animated text or VFX comps built or rendered with EffectCraft.
---

# EffectCraft via MCP

Server: `effectcraft` (`effectcraft-cli mcp`). Tested with effectcraft-cli 0.6.0 on Windows 11.

- **Modes:** headless by default. Add `--gpu` to render on the GPU (headless otherwise renders on the CPU),
  or `--bridge 9877` to drive an app started with `effectcraft --control 9877`.
- **Unknown options are rejected,** unlike PdfCraft.

## Tested workflow
1. `open_project {"new":true}`. You can also pass `demo: true` or `path` to an .ecproj file.
2. `execute_command {"command":"comp.new","params":{"name":"Main","width":1280,"height":720,"frameRate":24,"duration":3}}`
   → `{comp}`
3. Add layers. Each command returns `{layer}`:
   - `execute_command {"command":"layer.newSolid","params":{"color":"#3366ff"}}`
   - `execute_command {"command":"layer.newText","params":{"text":"Title","size":110,"fill":"#ffffff"}}`
4. Make bulk edits with `run_script`, which uses an After Effects-style object model.
   - Example: `{"code":"var c=app.project.activeItem; c.layers.addText('Hi'); c.numLayers"}`
   - The value of the last expression is returned. `writeLn` output is captured.
5. `render_frame {"time":1,"max_side":960}` returns a PNG. Add `"path"` to also write it to disk. Look at it.
6. Render video:
   - `execute_command {"command":"renderQueue.add","params":{"comp":"Main","format":"h264","output":"/abs/out.mp4"}}`
   - then `execute_command {"command":"renderQueue.render","params":{"wait":true}}`
   - The formats are h264, hevc, av1, prores, webm, png, jpeg, tiff, exr, gif, wav and aiff.
   - Check the file with ffprobe.
7. `save_project {"path":"/abs/out.ecproj"}`

## Notes
- **Discovering things:** `list_commands` / `describe_command` (about 665 commands), `list_effects`
  (306 effects), `list_fonts`, and `get_state` to re-orient after a series of edits.
- **Properties and keyframes:**
  - `get_property` / `set_property` / `add_keyframe` address a property by its path within a layer.
  - `get_layer` lists the available paths.
  - Keyframe tools use **layer time** while reads use comp time, so keys can land in the wrong place on
    offset layers (storytold/effectcraft#257).
- **Batching:** `batch` runs several commands as one undo step.
- **File access:** there is no sandbox (storytold/effectcraft#500).
