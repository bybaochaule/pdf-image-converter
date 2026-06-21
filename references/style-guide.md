# PDF Image Converter Style Guide

## Defaults

- Default format: `png`.
- Accepted formats: `png`, `jpeg`, `jpg`.
- Default DPI: `200`.
- Default JPEG quality: `90`.
- Default page selection: all pages.
- Default output directory for one PDF: `<pdf-stem>_images/`.
- Default output directory for multiple PDFs: one subfolder per PDF under the requested output root.

## Naming rules

Use stable, sortable page names:

```text
<pdf-stem>_page_0001.png
<pdf-stem>_page_0002.png
<pdf-stem>_page_0003.jpeg
```

For multiple PDFs, keep images separated by source PDF:

```text
rendered/
|-- report-a_images/
|   `-- report-a_page_0001.png
`-- report-b_images/
    `-- report-b_page_0001.png
```

## Page selection syntax

Pages are 1-indexed. Supported examples:

- `1`: page 1 only.
- `1,3,5`: pages 1, 3, and 5.
- `2-6`: pages 2 through 6.
- `1,4-7,10`: mixed single pages and ranges.
- `all`: all pages.

## Choosing output settings

- Use PNG for crisp text, forms, screenshots, diagrams, and lossless page previews.
- Use JPEG/JPG for smaller photographic or web preview outputs.
- Use 150 DPI for small previews or very large documents.
- Use 200 DPI for general-purpose conversion.
- Use 300 DPI or higher only when the user needs print-quality images and file size is acceptable.

## Edge cases

- Encrypted PDFs require a user-provided password and authorization.
- Corrupt PDFs may fail in one renderer and succeed in another; try the helper's fallback renderer when available.
- Very large PDFs can create many large images; use page ranges or lower DPI.
- Transparent PDF elements are rendered onto a white background for stable PNG and JPEG output.
- JPEG is lossy; tell the user when lossy output may affect sharp text or fine lines.

## Verification

Before returning final files:

1. Confirm the number of output images.
2. Open or inspect at least the first image.
3. Confirm format, extension, and output location.
4. Report any pages that failed.
5. ZIP outputs when file count is large or the user requested a package.

## Safety

- Do not remove encryption or bypass permissions.
- Do not reveal document content unless the user asked for a content summary.
- Do not expose passwords in logs or final messages.
- Do not delete original PDFs.
- Prefer local conversion over network services.
