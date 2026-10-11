---
name: pdfcraft
description: Unofficial third-party skill. Drive PdfCraft (open-source Acrobat-style PDF workbench) through its MCP server — create, read, extract text, render pages, add text/images, combine/split, forms, comments, redaction, OCR, PDF/A, compare and sign. Use when the user wants to read, build, edit, fill, redact, merge or inspect PDFs with PdfCraft.
---

# PdfCraft via MCP

Server: `pdfcraft`, launched by this plugin as `pdfcraft-cli mcp --compact`. Tested with 0.4.0 on Windows 11.

- **Compact mode:** `--compact` (core tools plus `tool_search` / `tool_call`) comes after 0.4.0. **0.4.0
  ignores the flag and lists all 131 tools.** That works, but the tool list is large.
- **No live bridge:** PdfCraft's MCP server is headless only.

## Tested workflow
1. Create or open a document:
   - `doc_create {"from":"blank","pages":2}` makes an unsaved blank PDF. You can also start `from` images
     (`paths`) or text.
   - `doc_open {"path":"/abs/in.pdf"}` opens an existing one.
   - Both return `{doc, pages, editable}`. Every later call takes that `doc` id.
2. `page_add_text {"doc":1,"page":1,"text":"Title\nline 2","at":[72,72],"size":24,"bold":true,"width":450}`
   - Coordinates are points measured from the top-left of the displayed page.
   - The font is helvetica, times or courier.
3. `doc_save {"doc":1,"path":"/abs/out.pdf"}` writes atomically. Saving to its own file is an incremental
   update, which keeps signatures valid.
4. Check the result:
   - `text_extract {"doc":N}` returns the text in reading order.
   - `page_render {"doc":N,"page":1,"dpi":96}` returns a PNG. Look at it.

## Common tasks
- **Structure:** `doc_combine`, `doc_split`, `page_extract`, `page_rotate`, `page_move`, `page_delete`,
  `page_insert_file`.
- **Forms:** `form_fields`, `form_fill`, `form_detect_fields`, `form_merge_data`.
- **Redaction:** `redact_mark`, then `redact_apply`. This is destructive, so render the page and check it
  before saving.
- **OCR and PDF/A:** `ocr_recognize`; `pdfa_verify` / `pdfa_convert`.
- **Accessibility:** `accessibility_check` / `accessibility_fix`.
- **Compare:** `doc_compare` / `doc_compare_report`.

## Security
- `--root DIR` confines reads and writes to DIR, and it works. Opening a file outside DIR fails with
  "outside the allowed directory".
- **However, 0.4.0 and 0.5.0 accept any unknown option without an error** (storytold/pdfcraft#640). A misspelt
  `--root` therefore starts the server unconfined. After changing flags, re-test by opening a file outside
  the root.
- `js_run` runs document JavaScript. Don't run scripts from untrusted PDFs.
