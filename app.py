import io
import os
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter


st.set_page_config(
    page_title="PDF Merge & Compress",
    page_icon="logo.png",
    layout="wide"
)

if Path("logo.png").exists():
    st.sidebar.image("logo.png", width=200)

st.sidebar.markdown("### Athina Logistics")
st.sidebar.caption("PDF Tool")

st.title("Merge & Compress PDF")
st.caption("Upload plusieurs PDF. L'app fusionne puis compresse fortement le fichier final.")


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


def compress_pdf_strong(pdf_bytes):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")

        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            "-dColorImageDownsampleType=/Bicubic",
            "-dColorImageResolution=100",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dGrayImageResolution=100",
            "-dMonoImageDownsampleType=/Subsample",
            "-dMonoImageResolution=150",
            f"-sOutputFile={output_path}",
            input_path,
        ]

        subprocess.run(cmd, check=True)

        with open(output_path, "rb") as f:
            return f.read()


def size_mb(data):
    return len(data) / 1024 / 1024


uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

output_name = st.text_input("Output filename", value="merged_compressed.pdf")

if not output_name.lower().endswith(".pdf"):
    output_name += ".pdf"

if uploaded_files:
    st.subheader("Uploaded files")

    for i, f in enumerate(uploaded_files, start=1):
        st.write(f"{i}. {f.name} - {f.size / 1024 / 1024:.2f} MB")

    if st.button("Merge and compress", type="primary"):
        try:
            merged = merge_pdfs(uploaded_files)
            compressed = compress_pdf_strong(merged)

            st.success("PDF created successfully.")

            c1, c2, c3 = st.columns(3)
            c1.metric("Uploaded files", len(uploaded_files))
            c2.metric("Before compression", f"{size_mb(merged):.2f} MB")
            c3.metric("After compression", f"{size_mb(compressed):.2f} MB")

            st.download_button(
                label="Download compressed PDF",
                data=compressed,
                file_name=output_name,
                mime="application/pdf",
            )

        except FileNotFoundError:
            st.error("Ghostscript is not installed. Vérifie que packages.txt contient bien: ghostscript")

        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.info("Upload at least one PDF.")
