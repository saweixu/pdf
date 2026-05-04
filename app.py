import io
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="PDF Merge & Ultra Compress",
    page_icon="logo.png",
    layout="wide"
)

if Path("logo.png").exists():
    st.sidebar.image("logo.png", width=200)

st.sidebar.markdown("### Athina Logistics")
st.sidebar.caption("PDF Tool")

st.title("Merge & Ultra Compress PDF")
st.caption("Upload PDF files → merge → ultra compress (very small size).")


# =========================
# HELPERS
# =========================
def get_prefix(filename):
    stem = Path(filename).stem
    return stem.split("-")[0].strip() if "-" in stem else stem.strip()


def size_mb(data):
    return len(data) / 1024 / 1024


def merge_pdfs(uploaded_files):
    writer = PdfWriter()

    for uploaded_file in uploaded_files:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


# =========================
# 🔥 ULTRA COMPRESSION
# =========================
def compress_pdf_ghostscript(pdf_bytes):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.pdf"
        output_path = Path(tmpdir) / "output.pdf"

        input_path.write_bytes(pdf_bytes)

        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",

            # compression ultra violente
            "-dDownsampleColorImages=true",
            "-dColorImageResolution=25",
            "-dDownsampleGrayImages=true",
            "-dGrayImageResolution=25",
            "-dDownsampleMonoImages=true",
            "-dMonoImageResolution=60",

            "-dAutoFilterColorImages=false",
            "-dAutoFilterGrayImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",

            # qualité JPEG très basse
            "-dJPEGQ=10",

            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",

            f"-sOutputFile={output_path}",
            str(input_path),
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        compressed = output_path.read_bytes()

        # sécurité : si Ghostscript donne un fichier plus gros, garder l'original fusionné
        if len(compressed) >= len(pdf_bytes):
            return pdf_bytes

        return compressed


# =========================
# UI
# =========================
uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:

    st.subheader("Uploaded files")

    for i, f in enumerate(uploaded_files, start=1):
        st.write(f"{i}. {f.name} - {f.size / 1024 / 1024:.2f} MB")

    prefix = get_prefix(uploaded_files[0].name)
    output_name = f"{prefix}_merged_compressed.pdf"

    st.info(f"Output filename: {output_name}")

    if st.button("Merge & Ultra Compress", type="primary"):

        try:
            with st.spinner("Merging PDFs..."):
                merged_bytes = merge_pdfs(uploaded_files)

            with st.spinner("Ultra compressing..."):
                compressed_bytes = compress_pdf_ghostscript(merged_bytes)

            st.success("PDF created successfully.")

            c1, c2 = st.columns(2)
            c1.metric("Merged size", f"{size_mb(merged_bytes):.2f} MB")
            c2.metric("Compressed size", f"{size_mb(compressed_bytes):.2f} MB")

            st.download_button(
                label="Download compressed PDF",
                data=compressed_bytes,
                file_name=output_name,
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("Upload PDF files to start.")
