# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import math
import re
import tempfile
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
import streamlit as st
from PIL import Image


APP_TITLE = "Athina PDF Compressor Online"


def mb(n: int) -> float:
    return n / (1024 * 1024)


def detect_prefix(filename: str) -> str:
    """
    Output name rule:
    take everything before '-' from the first uploaded PDF.
    If no '-', use filename stem.
    """
    stem = Path(filename).stem.strip()
    if "-" in stem:
        prefix = stem.split("-")[0].strip()
    else:
        prefix = stem[:30].strip()
    prefix = re.sub(r'[\\/:*?"<>|]+', "_", prefix)
    return prefix or "PDF"


def save_uploaded_files(uploaded_files, folder: Path) -> List[Path]:
    paths = []
    for uf in uploaded_files:
        p = folder / uf.name
        p.write_bytes(uf.getvalue())
        paths.append(p)
    return paths


def add_pdf_to_doc(output: fitz.Document, pdf_path: Path) -> int:
    src = fitz.open(str(pdf_path))
    output.insert_pdf(src)
    page_count = src.page_count
    src.close()
    return page_count


def merge_pdfs(pdf_paths: List[Path]) -> Tuple[bytes, int]:
    out = fitz.open()
    total_pages = 0
    for p in pdf_paths:
        total_pages += add_pdf_to_doc(out, p)

    data = out.tobytes(
        garbage=4,
        deflate=True,
        clean=True,
        linear=True,
    )
    out.close()
    return data, total_pages


def render_compress_pdf(
    pdf_bytes: bytes,
    dpi: int,
    jpeg_quality: int,
    grayscale: bool = True,
) -> bytes:
    """
    Strong compression:
    render each page as JPEG image, then rebuild one PDF.

    Warning:
    text becomes image, not searchable/copyable.
    """
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for page in src:
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        img = Image.open(io.BytesIO(pix.tobytes("png")))
        if grayscale:
            img = img.convert("L")
        else:
            img = img.convert("RGB")

        jpg_buf = io.BytesIO()
        img.save(
            jpg_buf,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True,
            progressive=True,
        )
        jpg_bytes = jpg_buf.getvalue()

        rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(rect, stream=jpg_bytes)

    final = out.tobytes(
        garbage=4,
        deflate=True,
        clean=True,
        linear=True,
    )

    src.close()
    out.close()
    return final


def compress_until_target(
    merged_bytes: bytes,
    target_mb: float,
    mode: str,
    progress=None,
) -> Tuple[bytes, str]:
    target_bytes = int(target_mb * 1024 * 1024)

    # First try normal PDF optimization without rasterizing
    best = merged_bytes
    best_tag = "Normal optimization"

    if len(best) <= target_bytes:
        return best, best_tag

    if mode == "Balanced":
        ladder = [
            (120, 35),
            (100, 30),
            (85, 25),
            (72, 22),
        ]
    elif mode == "Strong":
        ladder = [
            (100, 28),
            (85, 22),
            (72, 18),
            (60, 15),
        ]
    else:  # Extreme
        ladder = [
            (85, 20),
            (72, 15),
            (60, 12),
            (50, 10),
        ]

    total = len(ladder)

    for i, (dpi, quality) in enumerate(ladder, start=1):
        if progress:
            progress.progress(i / total, text=f"Compression render {dpi} dpi / quality {quality}")

        candidate = render_compress_pdf(
            merged_bytes,
            dpi=dpi,
            jpeg_quality=quality,
            grayscale=True,
        )

        if len(candidate) < len(best):
            best = candidate
            best_tag = f"Render {dpi} dpi / JPEG quality {quality}"

        if len(best) <= target_bytes:
            break

    return best, best_tag


st.set_page_config(page_title=APP_TITLE, page_icon="📄", layout="centered")

st.title("📄 Athina PDF Compressor Online")
st.caption("Upload plusieurs PDF → fusion → compression → téléchargement.")

uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

col1, col2 = st.columns(2)
with col1:
    target_mb = st.number_input("Target size MB", min_value=1.0, max_value=200.0, value=10.0, step=1.0)
with col2:
    mode = st.selectbox("Compression level", ["Balanced", "Strong", "Extreme"], index=1)

st.info(
    "Balanced = meilleure qualité. Strong = recommandé. Extreme = plus petit mais plus flou. "
    "Le mode render transforme le texte en image."
)

if uploaded_files:
    original_total = sum(len(f.getvalue()) for f in uploaded_files)
    prefix = detect_prefix(uploaded_files[0].name)

    st.write(f"**PDF count:** {len(uploaded_files)}")
    st.write(f"**Original total:** {mb(original_total):.2f} MB")
    st.write(f"**Output name:** `{prefix}-PDF compressed version.pdf`")

    if st.button("Compress PDF", type="primary"):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            pdf_paths = save_uploaded_files(uploaded_files, tmp)

            with st.spinner("Merging PDF files..."):
                merged_bytes, total_pages = merge_pdfs(pdf_paths)

            st.write(f"**Merged size:** {mb(len(merged_bytes)):.2f} MB")
            st.write(f"**Total pages:** {total_pages}")

            progress = st.progress(0, text="Starting compression...")
            final_bytes, strategy = compress_until_target(
                merged_bytes=merged_bytes,
                target_mb=target_mb,
                mode=mode,
                progress=progress,
            )
            progress.empty()

            final_name = f"{prefix}-PDF compressed version.pdf"
            saved = original_total - len(final_bytes)
            emails_needed = max(1, math.ceil(len(final_bytes) / (10 * 1024 * 1024)))

            st.success("Compression finished")
            st.write(f"**Final size:** {mb(len(final_bytes)):.2f} MB")
            st.write(f"**Saved:** {mb(saved):.2f} MB")
            st.write(f"**Strategy:** {strategy}")
            st.write(f"**Estimated emails needed ≤10MB:** {emails_needed}")

            st.download_button(
                label="Download compressed PDF",
                data=final_bytes,
                file_name=final_name,
                mime="application/pdf",
            )
else:
    st.warning("Upload at least one PDF.")
