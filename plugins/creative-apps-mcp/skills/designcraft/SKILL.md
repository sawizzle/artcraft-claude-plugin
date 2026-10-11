---
name: designcraft
description: Unofficial third-party skill. Drive DesignCraft (open-source InDesign-style page layout app) through its MCP server — create documents, text and graphic frames, styles, place images, render pages, and export PDF/PNG/IDML/EPUB/HTML. Use when the user wants a flyer, poster, magazine page, brochure or multi-page layout built or exported with DesignCraft.
---

# DesignCraft via MCP

Server: `designcraft` (`designcraft-cli mcp`). Tested with designcraft-cli 0.4.0 on Windows 11.

- **Modes:** headless by default. For the live app, start it with `designcraft --control <port>` and the
  server with `--connect <port>`.
- **Port clash:** the default port 7979 is the same as VectorCraft's.
- `--sample` opens the multi-page magazine sample.

## Tested workflow
1. `new_document {"width":612,"height":792}`. Sizes are in points (72 pt = 1 in). It also takes
   `margins`, `columns`, `gutter`, `facingPages`, `bleed`.
2. `execute {"command":"frame.create","params":{"rect":[54,54,558,200],"content":"text","text":"Headline"}}`
   → `{id, story}`. The `rect` is `[x0,y0,x1,y1]` in spread coordinates.
3. **Style text:** select the frame (or a text range), then call `type.char`:
   - `execute {"command":"selection.set","params":{"ids":[<frame id>]}}`
   - `execute {"command":"type.char","params":{"size":36,"fontFamily":"..."}}`. The form
     `{"attrs":{...}}` works too. An unknown attribute is rejected.
   - **Watch out:** `frame.create` with text leaves a **text caret** at the end of the new text. With a
     caret inside existing text, `type.char` returns `null` and **changes nothing**
     (storytold/designcraft#289). Select the frame first, as above. With nothing selected at all, the
     call fails with "select text or a text frame".
   - `null` is also what a successful call returns, so **check the result** with `render_page`.
4. `place_image {"path":"/abs/img.png","x":54,"y":240,"width":504}` places into a new frame. Pass `frame`
   to place into an existing one.
5. Check the layout:
   - `inspect_document` returns pages, spreads, items, stories (with `overset`) and styles.
   - `render_page {"page":0}` returns a PNG. Look at it, and check for overset text.
6. Export:
   - `export_png {"path":"/abs/p1.png","page":0,"scale":2}` writes a PNG.
   - `execute {"command":"file.exportPdf","params":{"path":"/abs/out.pdf"}}` writes a PDF.
   - Other formats: `file.exportIdml`, `file.exportEpub`, `file.exportHtml`.
7. `save_document {"path":"/abs/out.designcraft"}`

## Notes
- **Text:** `get_story` / `set_story_text {"frame":id,"text":"..."}` replace a story's text and keep its
  formatting. Use `\n` for paragraph breaks.
- **Commands:** `list_commands {"filter":"style"}` lists ids and params; `batch` runs several commands at once.
- **Known upstream bugs:** DesignCraft #61, #63, #69 and #70 are MCP correctness issues. Re-check results
  with `inspect_document` or `render_page`.
- **AMD GPUs:** if the GUI crashes on an AMD GPU (OpenGL), set `WGPU_BACKEND=dx12` (storytold/designcraft#167).
