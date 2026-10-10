---
name: filmcraft
description: Drive FilmCraft (open-source Premiere-style video editor) through its MCP server — import media, build sequences, razor/trim/apply effects, render frames, and export H.264/HEVC/ProRes/DNxHR video or EDL/XML/FCPXML/OTIO/AAF interchange. Use when the user wants to cut, assemble, inspect or export video with FilmCraft.
---

# FilmCraft via MCP

Server: `filmcraft` (`filmcraft-cli mcp`). Tested with filmcraft-cli 0.4.0 on Windows 11. It runs headless unless you
pass `--bridge 127.0.0.1:9876` and start the app with `filmcraft --control 9876`.

## Headless has no selection: always pass explicit ids
Many commands default to "the selected clip" or "the selected item". Headless, nothing is selected, so they
fail with `not available right now: select a clip in the Project panel`. Pass the ids yourself.

## Tested workflow
1. Import a clip with `media_import {"text":"/abs/clip.mp4"}` → `{"items":[1]}`. The argument is named
   `text` and holds one absolute path (storytold/filmcraft#499). For several files, or for bins and image
   sequences, use `command_run {"id":"file.import","params":{"paths":[...],"bin":id,"imageSequence":true}}`.
2. Make a sequence from it with `command_run {"id":"file.newSequenceFromClip","params":{"items":[1]}}`
   → `{sequence, clips}`. To make an empty one, use
   `file.newSequence {"name","width","height","fps","sampleRate"}`.
3. Edit, for example:
   - `command_run {"id":"timeline.razor","params":{"seconds":1.5}}`
   - Apply an effect. It needs `clips`, because there is no selection:
     `command_run {"id":"effects.apply","params":{"clips":[6],"effect":"Gaussian Blur"}}`.
     This returns `null` and adds the effect with its **defaults**. Gaussian Blur's blurriness defaults
     to 0, so nothing changes visibly until you set it.
   - Set an effect parameter with
     `command_run {"id":"effects.setParam","params":{"clip":6,"effect":"gaussian_blur","param":"blurriness","value":40}}`.
     `effect` is the effect **id** (as `sequence_inspect` lists it, e.g. `gaussian_blur`) or its index.
     The display label doesn't work here.
4. `sequence_inspect` returns tracks and clips. Times are in ticks (254016000000 = 1 s); most commands also
   accept `seconds`, `frame` or `timecode`.
5. `render_frame {"seconds":2,"max_side":960}` returns a PNG. Look at it.
6. Export with
   `command_run {"id":"file.exportMedia","params":{"path":"/abs/out.mp4","format":"h264","wait":true}}`.
   The formats are h264, hevc, prores, dnxhr, apv, mjpeg, mxf-op1a, mxf-opatom, png, tiff, bmp, gif, wav and aiff.
   Without `"wait": true` the call returns before the file is written.
   Check the result with ffprobe (fps, nb_frames, resolution).
7. Export interchange with `file.exportFcpxml`, `file.exportFcp7Xml`, `file.exportEdl`, `file.exportOtio`,
   `file.exportAaf` or `file.exportOmf`, each taking `{"path":...}`.

## Notes
- **Discovering commands:** `command_list {"filter":"export"}` lists ids and their params. The CLI equivalents
  are `filmcraft-cli commands <filter>` and `filmcraft-cli describe <id>`.
- **Export presets:** `export.presets.list`, then `file.exportMedia {"preset":name}`. There is also a queue:
  `export.queue.add`, then `export.queue.start`.
- **Live mode only:** `ui_*` tools such as `ui_screenshot`, `ui_click` and `ui_drag`. They are listed headless
  too, but they only act on a live window (`--bridge`).
- **File access:** `filmcraft-cli mcp` has no file sandbox. It accepts automation-root flags but ignores them
  (storytold/filmcraft#476).
