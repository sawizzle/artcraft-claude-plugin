---
name: filmcraft
description: Unofficial third-party skill. Drive FilmCraft (open-source Premiere-style video editor) through its MCP server — import media, build and edit sequences (razor, trim, effects, audio), render frames, and export H.264/HEVC/ProRes/DNxHR/WAV video or EDL/FCP7 XML/FCPXML/OTIO/AAF interchange. Also covers working safely beside a human in the live app (--bridge) and observing their edits. Use when the user wants to cut, assemble, inspect, export or watch edits in FilmCraft.
---

# FilmCraft via MCP

Server: `filmcraft` (`filmcraft-cli mcp`). Tested with filmcraft-cli 0.5.0 on Windows 11 (2026-10-10), headless.
Bridge and live-app notes come from a live session (not re-checked). It runs headless unless you pass
`--bridge 127.0.0.1:9876` and the app is running with `filmcraft --control 9876`. Headless exposes 675 commands
and gives repeatable exports; the bridge should match (not re-checked). Only the `ui_*` tools need the live window.

## Ground rules
- **Health check first.** Call `project_inspect` before any edit. In bridge mode, a `bridge: cannot connect ...`
  isError (after about 2 s) means the app is not running. There is no headless fallback.
- **Read back every edit.** `ok:true` is not proof. Inside `command_run.params`, misspelled or wrong-typed
  **optional** keys (`seconds`, `frame`, `track`, `name`...) are silently ignored, so the edit lands at the
  playhead or a default. Required params (`clip`, `effect`, `param`, `value`) return an error instead. Send real
  JSON numbers, then re-read the field you changed.
- **Look at renders, ffprobe exports.** Open frames from `render_frame`. Check exported files for fps, frame count
  and resolution, and measure audio levels.
- **Headless has no selection.** Pass ids yourself: `clips`, `clip`, `items`, `track`.

## Tested workflow (0.5.0)
1. Import one file: `media_import {"text":"C:/abs/clip.mp4"}` → `{"errors":[],"items":[1]}`. The argument is named
   `text` (storytold/filmcraft#499). For several files or bins, use
   `command_run {"id":"file.import","params":{"paths":[...]}}`. `file.import` returns `ok:true` even when
   `errors[]` or `documents[].offlineMedia[]` is non-empty, so check both.
2. Make a sequence: `command_run {"id":"file.newSequenceFromClip","params":{"items":[1]}}` →
   `{"sequence":4,"clips":[6,7]}` (video 6, linked audio 7). Ids are from a fresh session with one
   import: read them from the result.
3. Edit, for example:
   - `timeline.razor {"seconds":1.5}` → `{"cuts":2}`, which splits the video and its linked audio.
   - `effects.apply {"clips":[6],"effect":"Gaussian Blur"}` returns `null` and adds the effect at its
     **defaults**. Gaussian Blur's blurriness defaults to 0, so nothing is visible yet.
   - Set the parameter with `effects.setParam {"clip":6,"effect":"gaussian_blur","param":"blurriness","value":40}`.
     `effect` is the effect **id** from `sequence_inspect` (or its index), not the display label.
   - Mute an audio track with `timeline.setTrack {"track":"A1","muted":true}` (or `mixer.setStrip`).
     `track` takes a name (`A1`) or the audio track id from `sequence_inspect`. `enabled:false` on an audio track
     does **not** silence it.
4. Read back: `sequence_inspect` (times are in ticks: 254016000000 = 1 s), plus `command_run history.list`.
5. Look: `render_frame {"seconds":0.5,"max_side":960}` returns a PNG. Do not pass `max_side:0` on 0.5.0 (it
   errors, storytold/filmcraft#459). Omit `max_side` for the default of 960.
6. Export: `file.exportMedia {"path":"C:/abs/out.mp4","format":"h264","wait":true}` returns `result.frames`.
   - The formats are h264, hevc, prores, dnxhr, apv, mjpeg, mxf-op1a, mxf-opatom, png, tiff, bmp, gif, wav and aiff.
     HEVC worked on 0.5.0 (software encoding).
   - A mismatched extension gets the container extension appended, and png/tiff/bmp write numbered frames. Read
     the returned path.
   - Presets: `export.presets.list`, then `file.exportMedia {"path":..,"preset":"<exact name>","wait":true}`.
   - A sub-range: add `"startSeconds":1.0,"endSeconds":2.0`. The end is exclusive (24 frames at 24 fps), and no
     `range` key is needed.
7. Interchange: `file.exportEdl`, `file.exportFcp7Xml`, `file.exportFcpxml`, `file.exportOtio` and
   `file.exportAaf`, each `{"path":...}`. All five re-import as sequences on 0.5.0. `file.exportOmf` and
   `file.exportInterchange` also exist.
   - The EDL holds one video track (V1). Other video tracks are dropped (the export report says so), and audio
     events are kept.
   - Marker colour is lost in every interchange format (re-imports as Blue). Marker duration survives FCPXML, FCP7
     XML, OTIO and AAF, but not EDL.
   - EDL and OTIO media refs are relative (`../media/...`), so they break if the export folder moves.

## Units and time
- Time params accept these forms:
  - Most commands accept `time` (ticks), `seconds`, `frame` or `timecode`.
  - `graphics.newText {seconds}` is the **duration**, while `frame` and `timecode` give the start.
  - `source.setPlayhead` has no `timecode` param: passing it resets the source playhead to 0. Use `seconds`,
    `frame` or `time`.
  - `00:00:01:29` at 24 fps rolls over (to frame 53) instead of erroring.
- Audio units:
  - `volume`, `audioGain`, `volumeDb` and `channel_volume` are dB.
  - Track and strip pan is clamped to -100..+100. The panner effect `balance` is not (500 applies, about +3 dB).
- Motion units: position is in sequence pixels, scale is in %, and rotation is in degrees clockwise.
- Stored `keyframes[].time` and the `mediaTime` input of `setKeyframe`, `deleteKeyframe` and `setInterpolation`
  are clip **media** time: `(seq - start) + in`. `effects.addKeyframe` and `effects.setParam` take sequence `time`.
  - `sequence_inspect` shows only keyframe counts. To read the times, `file.saveCopy` to a temp `.fcproj` and read
    `keyframes[].time`.
  - `deleteKeyframe` at a wrong `mediaTime` returns ok and does nothing, so re-check the count.

## Exports and files
- Never use `wait:false` and then end the session: the export is silently dropped. Use `wait:true`, or poll
  `jobs.list` until `finished:true`.
- `jobs.cancel` leaves an undecodable partial file. MCP `notifications/cancelled` cancels the job and deletes the
  partial.
- Ranges:
  - Without a range, `file.exportMedia` exports In/Out when they are marked. In/Out is out-inclusive.
  - `range:"workArea"` errors, and headless cannot set a work area.
  - `makeSubclip` `endFrame` is exclusive.
- Every export and save overwrites existing files silently, so use unique output paths.
  - Windows only: a `:` in a filename writes an NTFS alternate stream and still returns ok.
  - Windows only: a trailing dot is dropped for save and interchange paths, but `file.exportMedia` appends the
    extension (`name.mp4..mp4`). Avoid trailing dots.
- MOV and MP4 exports carry no timecode track. Use `mxf-op1a` when TC matters. The sequence start TC is not
  exposed by any inspect call.
- Import notes:
  - MP3 keeps its encoder delay (audio about 23-25 ms late), so convert to WAV with ffmpeg first.
  - VFR media is time-mapped but reported as CFR.
  - Re-importing a path duplicates the item.
- `clip.updateMetadata` writes `<media-stem>.xmp` next to the **source** media (`clip.mp4` -> `clip.xmp`) and
  skips if another app wrote one. Only run it on copies.

## Timeline, ids and undo
- `timeline.place` on V2 or above needs an explicit `audioTrack`. Without it, the linked audio overwrites A1,
  including another clip's audio.
  - `timeline.move` reports `overwritten[]`, but `timeline.place` does not.
  - After overwrite edits, scan for clips with `durationFrames <= 1` (slivers) (not re-checked).
- Clip and marker ids freed by undo are **reused** by the next edit. Re-read ids after every undo.
- `edit.duplicate` of a sequence (headless: `project.select {"items":[id]}` first) reuses the source's clip ids.
  Clip-id commands act on the **active** sequence: check `project_inspect.activeSequence` or call `sequence.open`
  first.
- `command_batch`:
  - Steps see the previous step's state.
  - To append, put `playhead.end` before each timeline-less `timeline.place`.
  - On failure it returns `isError` with `completed` = steps that succeeded, and exactly that many undos restore
    the pre-batch state.
- `project_inspect.revision` counts changes. It increments on edit, undo **and** redo, but not on playhead, snap or
  select. Equal content does not mean equal revision.
- Without a selection:
  - `edit.copy` and `edit.cut` take no ids, so call `timeline.select {"clips":[...]}` first.
  - `edit.label` with nothing selected returns ok and does nothing.

## Where state lives
`doc_inspect` misses a lot. Use these instead:

| State | Command |
|---|---|
| Captions | `captions.list` |
| Media paths | `media.status` (`project_inspect` has none) |
| Item marks and timecode | `project.items` |
| Metadata | `metadata.get` |
| Mixer lanes, sends, lane keyframes | `mixer.inspect` |
| Essential sound | `essentialSound.inspect` |
| Masks | `masks.list` |
| Graphic layers | `graphics.list` |
| Anything else | the saved project JSON |

`sequence_inspect` costs about 2 KB per clip.

Headless limits:
- `prefs.set` wrote no prefs file in a headless run with an isolated data dir.
- The 0.5.0 build has no whisper, so `sequence.transcribe` and `transcript.generate` fail cleanly. Use
  `transcript.set`.
- `masks.track` and `clip.sceneEditDetection` are jobs. A failed track returns `ok:true` with
  `status.result.error`.

## Live app (bridge) — working beside a human
- **Launch for agents (Windows):** `filmcraft.exe --control 9876 --data-dir <scratch dir> --empty --no-recover`.
  It listens on 127.0.0.1 within about 0.5 s and skips the "Recover Unsaved Changes" modal.
  - Use a throwaway `<scratch dir>`, never the user's profile, and `--no-recover` only on an app you launched.
  - MCP side: `filmcraft-cli mcp --bridge 127.0.0.1:9876`. A non-loopback address makes the server exit. Keep
    the control port on loopback.
  - Record the PID. Close only an instance you launched; closing loses its unsaved work.
  - The port allows 16 connections and never closes idle ones, so close raw sockets promptly.
- **Never** call `file.save`, `file.saveAs`, `file.saveCopy`, `file.open` or `file.import` without a `path` over the
  bridge. Each opens a native dialog that freezes every control connection, and `ui_key Escape` cannot dismiss it.
  - `file.newSequence {}` opens an in-app dialog instead (reply `{"dialog":"newSequence"}`). `ui_key Escape`
    closes it.
- Engine writes run underneath open in-app dialogs. Check `ui_inspect.dialog` before writing while a human is
  at the GUI.
- `app: timeout` (60 s, when the UI thread is blocked) does **not** mean the command failed. The command stays
  queued and runs later, and the client may resend once (worst case 180 s and a duplicate). Re-read
  `history.list` and `project_inspect` before retrying.
- **Optimistic concurrency:** record `project_inspect.revision` when planning. Re-read it right before writing. If
  it moved, stop and diff.
- `file.open` silently discards unsaved changes. Check `project_inspect.dirty` and ask the user first.
- The GUI does not watch the `.fcproj` on disk. A GUI save overwrites another writer's saved edits, so keep one
  writer per file.
- If the app is restarted on the same port, the bridge session silently talks to the new instance. Detect this
  when the revision goes backwards or the path or name changes.
- `file.saveCopy {"path":...}` leaves the GUI's path, dirty flag and revision unchanged. Use it to snapshot, then
  analyse the copy with a separate headless `filmcraft-cli mcp --project <copy>`.
- Bridge `render_frame` returns a Program-monitor screenshot with UI chrome, and it can move the user's playhead.
  For clean frames, render headlessly from a saveCopy.
- **Markers:** `markers.clearCurrent` removes **every** marker on the playhead frame, and there is no delete-by-id.
  - Prefix agent markers with `CLAUDE: `, and nudge one by +1 frame if a human marker sits on that frame.
  - Never use `markers.clearAll`.
  - Tell the user that unsaved agent markers vanish if they close without saving.
- Driving the UI:
  - `ui_elements {"prefix":"timeline.clip.<id>"}` gives `rect [x,y,w,h]`; timeline seconds = dx / `ui.timeline.pps`.
  - `ui_drag {"from":{"id":"timeline.clip.<id>"},"to":{x,y},"steps":n}` moves a clip like a mouse.

## Observing a human's edits (observed loop, not re-checked)
Watching a person's edits needs their consent: tell them.
One persistent `--bridge` session caught all 26 edits a scripted "human" made. These included trims, ripple,
roll, slip, razor, moves, re-source, speed and reverse, effects and params, transitions, mixer mute, solo and dB,
renames, markers, track inserts, and undo.
- **Tick (about 1 s):**
  - `command_run perf.stats` → `monitor.projectRevision` and `monitor.playheadFrame` (about 2.4 KB;
    headless `perf.stats` has no `monitor` key).
  - `project_inspect` only when the revision moves (and every 10th poll).
  - Optionally `ui_inspect` (about 11 KB) for attention: playhead, `playback.playing`, `ui.timeline.pps`,
    `ui.tool`, `ui.focused`, `dialog`.
- **Dump on revision change** (under 60 ms, about 25 KB on a small project):
  - `state.inspect` (open sequences);
  - `sequence.inspect {"item":id}` for each open sequence, always by explicit id;
  - `mixer.inspect`, `project_inspect`, `media.status` and `history.list`.
  - Light summaries must hash effect params, or `effects.setParam` edits are invisible.
- **Diff keys:**
  - clips by id with the track as an attribute, so a track change is a move;
  - tracks and mixer strips by id;
  - markers by (time, name, comment).
  - Because ids are reused after undo, confirm each id match with the content signature (item, track, start,
    sourceIn, sourceOut). Otherwise treat it as delete + add.
- **Re-baseline** on any of these:
  - an undo in `history.list`;
  - the revision moving more than history grew;
  - a path change;
  - the revision going backwards.
- **Filter your own writes:** use the revision span of each of your own commands, plus anything named `CLAUDE: `.
- **Stop:**
  1. `file.saveCopy` into a session folder.
  2. Run headless on the copy: an export with `wait:true` to a unique path, a 1 fps contact sheet from
     `render_frame`, and soloed WAV stems per track.
  3. Add any `CLAUDE: ` markers last, then read them back from `sequence.inspect`.
- Sampling at 1 s misses fast tool switches. Revision cannot prove content equality.

## Notes
- **Discovering commands:** `command_list {"filter":"export"}`, or `filmcraft-cli commands <filter>` and
  `filmcraft-cli describe <id>`.
- **File access:** `filmcraft-cli mcp` has no file sandbox. It accepts automation-root flags but ignores them
  (storytold/filmcraft#476).
