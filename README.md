# PDF Image Converter

## Overview

This Agent Skill converts PDF pages into PNG, JPEG, or JPG image files. It is designed for page rendering, preview generation, and batch PDF-to-image conversion.

## When to use

Use this skill when a user asks to convert PDF files or selected PDF pages to images, including prompts such as:

- "Convert this PDF to PNG."
- "Export each page as a JPEG."
- "Make page previews from these PDFs."
- "Batch-convert all PDFs to images and zip them."

Do not use this skill for OCR, text extraction, PDF editing, image-to-PDF conversion, or bypassing access controls.

## Contents

- `SKILL.md`: agent-facing instructions, trigger description, workflow, output requirements, and safety rules.
- `README.md`: this human-readable overview.
- `agents/openai.yaml`: OpenAI metadata and invocation policy.
- `references/style-guide.md`: conversion defaults, naming rules, examples, and edge cases.
- `scripts/pdf_to_images.py`: deterministic PDF-to-PNG/JPEG helper script.
- `scripts/example_helper.py`: minimal safe placeholder.
- `assets/`: reserved for reusable sample files or templates.

## Requirements for the helper script

The helper script uses one of these local renderers:

1. PyMuPDF (`fitz`), preferred.
2. Poppler `pdftoppm` and `pdfinfo`, fallback when available.

For JPEG output, Pillow is used only when the active PyMuPDF version does not provide direct JPEG saving.

## Usage examples

Convert all pages to PNG at 200 DPI:

```bash
python scripts/pdf_to_images.py input.pdf --format png --dpi 200 --out-dir output_images
```

Convert all pages to JPEG at 200 DPI and quality 90:

```bash
python scripts/pdf_to_images.py input.pdf --format jpeg --quality 90 --dpi 200 --out-dir output_images
```

Convert selected pages using 1-indexed page syntax:

```bash
python scripts/pdf_to_images.py input.pdf --pages 1,3-5 --format png --out-dir selected_pages
```

Convert multiple PDFs and create a ZIP archive:

```bash
python scripts/pdf_to_images.py file1.pdf file2.pdf --format jpg --dpi 150 --out-dir rendered --zip
```

## Package structure

```text
pdf-image-converter/
|-- SKILL.md
|-- README.md
|-- agents/
|   `-- openai.yaml
|-- assets/
|   `-- .gitkeep
|-- references/
|   `-- style-guide.md
`-- scripts/
    |-- example_helper.py
    `-- pdf_to_images.py
```
