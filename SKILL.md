---
name: pdf-image-converter
description: Use this skill to convert PDF pages into PNG or JPEG image files. Trigger when the user asks to render PDFs, export PDF pages as images, convert PDF to PNG, JPEG, or JPG, create page previews, or batch-convert PDF files. Do not use it for OCR, text extraction, PDF editing, or image-to-PDF conversion unless explicitly requested.
---

# PDF Image Converter

## Purpose

Convert one or more PDF files into raster image files, with one output image per selected page. Preserve the visible page appearance as closely as possible and make the conversion reproducible with explicit format, DPI, page range, naming, and verification steps.

## When to use

Use this skill when the user asks to:

- Convert a PDF, multiple PDFs, or selected PDF pages to PNG, JPEG, or JPG images.
- Render PDF pages as page previews, thumbnails, screenshots, or web-ready images.
- Batch-convert uploaded PDF files into image folders or a ZIP archive.
- Control image output settings such as DPI, page range, JPEG quality, or output directory.

## Do not use

Do not use this skill when:

- The user needs OCR, text extraction, table extraction, form extraction, or semantic document understanding.
- The user wants to edit, merge, split, redact, repair, compress, or otherwise modify a PDF.
- The user wants to convert images or office documents into a PDF.
- The input is not a PDF file and no PDF conversion step was requested.
- The file appears encrypted, restricted, or private and the user has not provided authorization or a valid password.

## Required inputs

Use information already provided by the user when possible. Required or defaulted inputs are:

- Source PDF file path or uploaded PDF file.
- Target image format: `png`, `jpeg`, or `jpg`; default to `png` when unspecified.
- Page selection: all pages by default, or a 1-indexed page list such as `1,3-5`.
- DPI or resolution: default to `200` DPI for general use; use lower DPI for very large PDFs and higher DPI for print-quality output.
- Output location: default to `<pdf-stem>_images/` and one image per page.
- JPEG quality when using JPEG/JPG: default to `90`.
- Password only when the PDF is encrypted and the user is authorized to open it.

## Workflow

1. Confirm the request is a PDF-to-image conversion task and identify the source PDF files.
2. Resolve missing settings safely:
   - Use `png` unless the user asked for `jpeg` or `jpg`.
   - Use 200 DPI unless the user requested another resolution.
   - Convert all pages unless the user requested a subset.
   - Name outputs as `<pdf-stem>_page_0001.<ext>`.
3. Create a clean output folder. For multiple PDFs, place each PDF's images in a separate subfolder.
4. Run the deterministic helper script when local execution is available:

   ```bash
   python scripts/pdf_to_images.py input.pdf --format png --dpi 200 --out-dir output_images
   ```

   For JPEG:

   ```bash
   python scripts/pdf_to_images.py input.pdf --format jpeg --quality 90 --dpi 200 --out-dir output_images
   ```

   For selected pages:

   ```bash
   python scripts/pdf_to_images.py input.pdf --pages 1,3-5 --format png --dpi 200 --out-dir output_images
   ```

5. Prefer the helper script's PyMuPDF renderer. If PyMuPDF is unavailable, the helper falls back to Poppler `pdftoppm` when installed.
6. Verify the output:
   - Count the generated image files and compare them with the selected page count.
   - Open or inspect at least the first generated image.
   - Confirm naming, extension, DPI choice, and output directory.
7. Package images as a ZIP only when requested or when many output files would be inconvenient to return individually.
8. Return links to the generated image files or ZIP archive, plus a short summary of format, DPI, pages converted, and any warnings.

## Output format

Return a concise final answer with:

- A link to the output folder, image files, or ZIP archive.
- Format, DPI, page range, and file count.
- Any assumptions, skipped files, encryption/password issues, or conversion warnings.

## Quality checklist

Before finalizing:

- The input file paths exist and are PDF files.
- The requested format is normalized to PNG or JPEG/JPG.
- The output directory exists and contains the expected number of image files.
- Each image file has a stable, page-numbered name.
- The first output image opens successfully.
- Large PDFs were handled with an appropriate DPI or page subset.
- Temporary files were not returned as final artifacts.
- Validation errors are reported clearly instead of being hidden.

## Safety and privacy

- Do not expose secrets, credentials, private document contents, or passwords in final responses.
- Do not bypass PDF access restrictions or remove encryption.
- Do not run destructive shell commands or delete user files.
- Avoid network access; conversion should be local and deterministic.
- Do not collect passwords unless the PDF is encrypted and the user confirms authorization.
- Keep generated files in the requested output folder or a safe working directory.
