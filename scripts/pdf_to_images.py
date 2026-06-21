#!/usr/bin/env python3
"""Convert PDF pages to PNG or JPEG image files.

The script prefers PyMuPDF and falls back to Poppler pdftoppm when available.
It never deletes source PDFs and writes outputs only to the requested directory.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


SUPPORTED_FORMATS = {"png", "jpeg", "jpg"}


def sanitize_stem(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-._")
    return cleaned or "pdf"


def normalize_format(value: str) -> Tuple[str, str]:
    fmt = value.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {value}. Use png, jpeg, or jpg.")
    if fmt == "png":
        return "png", "png"
    if fmt == "jpg":
        return "jpeg", "jpg"
    return "jpeg", "jpeg"


def parse_page_spec(spec: Optional[str], page_count: Optional[int]) -> Optional[List[int]]:
    """Return 0-indexed page indexes, or None to mean all pages when count is unknown."""
    if spec is None or spec.strip() == "" or spec.strip().lower() == "all":
        if page_count is None:
            return None
        return list(range(page_count))

    pages: List[int] = []
    seen = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            if not start_raw and not end_raw:
                raise ValueError(f"Invalid page range: {part}")
            start = int(start_raw) if start_raw else 1
            if end_raw:
                end = int(end_raw)
            else:
                if page_count is None:
                    raise ValueError(f"Open-ended page range needs a known page count: {part}")
                end = page_count
        else:
            start = end = int(part)

        if start < 1 or end < 1 or start > end:
            raise ValueError(f"Invalid page selection: {part}")
        if page_count is not None and end > page_count:
            raise ValueError(f"Page selection {part} exceeds PDF page count {page_count}")
        for page_number in range(start, end + 1):
            index = page_number - 1
            if index not in seen:
                pages.append(index)
                seen.add(index)

    if not pages:
        raise ValueError("No pages selected.")
    return pages


def ensure_output_path(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output exists; use --overwrite to replace it: {path}")


def save_pixmap_as_image(pix, out_path: Path, image_format: str, quality: int) -> None:
    if image_format == "png":
        pix.save(str(out_path))
        return

    # JPEG requires RGB and no alpha channel.
    import fitz  # type: ignore

    if getattr(pix, "alpha", 0) or getattr(getattr(pix, "colorspace", None), "n", 3) != 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    if hasattr(pix, "pil_save"):
        pix.pil_save(str(out_path), format="JPEG", quality=quality)
        return

    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("Pillow is required for JPEG output with this PyMuPDF version.") from exc

    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    image.save(str(out_path), format="JPEG", quality=quality)


def render_with_pymupdf(
    pdf_path: Path,
    out_dir: Path,
    stem: str,
    image_format: str,
    extension: str,
    dpi: int,
    pages_spec: Optional[str],
    quality: int,
    password: Optional[str],
    overwrite: bool,
) -> List[Path]:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    try:
        if getattr(doc, "needs_pass", False):
            if not password:
                raise RuntimeError("PDF is encrypted; provide --password only if authorized.")
            if not doc.authenticate(password):
                raise RuntimeError("The supplied PDF password did not unlock the file.")

        pages = parse_page_spec(pages_spec, doc.page_count)
        assert pages is not None
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        out_dir.mkdir(parents=True, exist_ok=True)
        generated: List[Path] = []

        for page_index in pages:
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = out_dir / f"{stem}_page_{page_index + 1:04d}.{extension}"
            ensure_output_path(out_path, overwrite)
            save_pixmap_as_image(pix, out_path, image_format, quality)
            generated.append(out_path)
        return generated
    finally:
        doc.close()


def get_page_count_with_pdfinfo(pdf_path: Path, password: Optional[str]) -> Optional[int]:
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return None
    command = [pdfinfo]
    if password:
        command.extend(["-upw", password])
    command.append(str(pdf_path))
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        return None
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def run_pdftoppm(command: Sequence[str]) -> None:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown pdftoppm error"
        raise RuntimeError(message)


def sort_pdftoppm_outputs(paths: Iterable[Path]) -> List[Path]:
    def key(path: Path) -> Tuple[int, str]:
        match = re.search(r"-(\d+)\.[^.]+$", path.name)
        return (int(match.group(1)) if match else 0, path.name)

    return sorted(paths, key=key)


def page_number_from_pdftoppm(path: Path, default_number: int) -> int:
    match = re.search(r"-(\d+)\.[^.]+$", path.name)
    return int(match.group(1)) if match else default_number


def render_with_pdftoppm(
    pdf_path: Path,
    out_dir: Path,
    stem: str,
    image_format: str,
    extension: str,
    dpi: int,
    pages_spec: Optional[str],
    quality: int,
    password: Optional[str],
    overwrite: bool,
) -> List[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("Neither PyMuPDF nor Poppler pdftoppm is available for PDF rendering.")

    page_count = get_page_count_with_pdfinfo(pdf_path, password)
    pages = parse_page_spec(pages_spec, page_count)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []

    with tempfile.TemporaryDirectory(prefix="pdf_to_images_", dir=str(out_dir)) as tmp:
        tmp_dir = Path(tmp)
        base_command = [pdftoppm, "-r", str(dpi)]
        if image_format == "png":
            base_command.append("-png")
        else:
            base_command.extend(["-jpeg", "-jpegopt", f"quality={quality}"])
        if password:
            base_command.extend(["-upw", password])

        if pages is None:
            prefix = tmp_dir / stem
            command = [*base_command, str(pdf_path), str(prefix)]
            run_pdftoppm(command)
            rendered = sort_pdftoppm_outputs(tmp_dir.glob(f"{stem}-*.{extension}"))
            if image_format == "jpeg" and not rendered and extension == "jpeg":
                rendered = sort_pdftoppm_outputs(tmp_dir.glob(f"{stem}-*.jpg"))
            for ordinal, rendered_path in enumerate(rendered, start=1):
                page_number = page_number_from_pdftoppm(rendered_path, ordinal)
                out_path = out_dir / f"{stem}_page_{page_number:04d}.{extension}"
                ensure_output_path(out_path, overwrite)
                shutil.move(str(rendered_path), str(out_path))
                generated.append(out_path)
        else:
            for page_index in pages:
                page_number = page_index + 1
                prefix = tmp_dir / f"{stem}_{page_number:04d}"
                command = [*base_command, "-f", str(page_number), "-l", str(page_number), str(pdf_path), str(prefix)]
                run_pdftoppm(command)
                matches = list(tmp_dir.glob(f"{prefix.name}-*.{extension}"))
                if image_format == "jpeg" and not matches and extension == "jpeg":
                    matches = list(tmp_dir.glob(f"{prefix.name}-*.jpg"))
                if not matches:
                    raise RuntimeError(f"pdftoppm did not create an image for page {page_number}")
                rendered_path = sort_pdftoppm_outputs(matches)[0]
                out_path = out_dir / f"{stem}_page_{page_number:04d}.{extension}"
                ensure_output_path(out_path, overwrite)
                shutil.move(str(rendered_path), str(out_path))
                generated.append(out_path)

    if not generated:
        raise RuntimeError("No image files were generated.")
    return generated


def convert_pdf(
    pdf_path: Path,
    out_dir: Path,
    requested_format: str,
    dpi: int,
    pages_spec: Optional[str],
    quality: int,
    password: Optional[str],
    prefix: Optional[str],
    overwrite: bool,
) -> List[Path]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"PDF path is not a file: {pdf_path}")

    image_format, extension = normalize_format(requested_format)
    stem = sanitize_stem(prefix or pdf_path.stem)

    try:
        return render_with_pymupdf(
            pdf_path=pdf_path,
            out_dir=out_dir,
            stem=stem,
            image_format=image_format,
            extension=extension,
            dpi=dpi,
            pages_spec=pages_spec,
            quality=quality,
            password=password,
            overwrite=overwrite,
        )
    except ImportError:
        return render_with_pdftoppm(
            pdf_path=pdf_path,
            out_dir=out_dir,
            stem=stem,
            image_format=image_format,
            extension=extension,
            dpi=dpi,
            pages_spec=pages_spec,
            quality=quality,
            password=password,
            overwrite=overwrite,
        )
    except Exception as exc:
        if shutil.which("pdftoppm"):
            print(f"warning: PyMuPDF rendering failed, trying pdftoppm fallback: {exc}", file=sys.stderr)
            return render_with_pdftoppm(
                pdf_path=pdf_path,
                out_dir=out_dir,
                stem=stem,
                image_format=image_format,
                extension=extension,
                dpi=dpi,
                pages_spec=pages_spec,
                quality=quality,
                password=password,
                overwrite=overwrite,
            )
        raise


def make_zip(out_root: Path, image_paths: Sequence[Path], overwrite: bool) -> Path:
    zip_path = out_root.parent / f"{out_root.name}.zip"
    ensure_output_path(zip_path, overwrite)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_path in image_paths:
            archive.write(image_path, image_path.relative_to(out_root))
    return zip_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG, JPEG, or JPG images.")
    parser.add_argument("pdf", nargs="+", help="Input PDF file path(s).")
    parser.add_argument("--out-dir", default=None, help="Output directory. Defaults to <pdf-stem>_images for one PDF or pdf_images for many.")
    parser.add_argument("--format", default="png", choices=sorted(SUPPORTED_FORMATS), help="Output image format.")
    parser.add_argument("--dpi", type=int, default=200, help="Render resolution in dots per inch.")
    parser.add_argument("--pages", default=None, help="1-indexed pages, for example: all, 1, 1,3-5, or 2-.")
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality from 1 to 100.")
    parser.add_argument("--password", default=None, help="Password for encrypted PDFs, only when authorized.")
    parser.add_argument("--prefix", default=None, help="Output filename prefix. Only valid with one input PDF.")
    parser.add_argument("--zip", action="store_true", help="Create a ZIP archive containing the generated images.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output images or ZIP archive.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dpi <= 0:
        parser.error("--dpi must be a positive integer.")
    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100.")
    if args.prefix and len(args.pdf) > 1:
        parser.error("--prefix can only be used with one input PDF.")

    pdf_paths = [Path(item).expanduser().resolve() for item in args.pdf]
    if args.out_dir:
        out_root = Path(args.out_dir).expanduser().resolve()
    elif len(pdf_paths) == 1:
        out_root = Path.cwd() / f"{sanitize_stem(pdf_paths[0].stem)}_images"
    else:
        out_root = Path.cwd() / "pdf_images"

    all_images: List[Path] = []
    failures: List[str] = []

    for pdf_path in pdf_paths:
        target_dir = out_root if len(pdf_paths) == 1 else out_root / f"{sanitize_stem(pdf_path.stem)}_images"
        try:
            images = convert_pdf(
                pdf_path=pdf_path,
                out_dir=target_dir,
                requested_format=args.format,
                dpi=args.dpi,
                pages_spec=args.pages,
                quality=args.quality,
                password=args.password,
                prefix=args.prefix,
                overwrite=args.overwrite,
            )
            all_images.extend(images)
        except Exception as exc:
            failures.append(f"{pdf_path}: {exc}")

    for image_path in all_images:
        print(image_path)

    if args.zip and all_images:
        zip_path = make_zip(out_root, all_images, args.overwrite)
        print(zip_path)

    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        return 1
    if not all_images:
        print("error: no images generated", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
