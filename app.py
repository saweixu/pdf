import io
from pathlib import Path

import fitz  # PyMuPDF
import streamlit as st
from pypdf import PdfReader, PdfWriter
from PIL import Image


st.set_page_config(
    page_title="PDF Merge & Extreme Compress",
    page_icon="logo.png",
    layout="wide"
)

if Path("logo.png").exists():
    st.sidebar.image("logo.png", width=200)

st.sidebar.markdown("### Athina Logistics")
st.sidebar.caption("Global Access")

st.title("Merge & Extreme Compress PDF")
st.caption("Upload PDF files → merge → convert pages to low-quality images → small PDF.")


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


def extreme_compress_by_rasterizing(pdf_bytes, zoom=0.75, jpeg_quality=80):
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()

    for page in src:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        img_buffer = io.BytesIO()
        img.save(
            img_buffer,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True
        )
        img_buffer.seek(0)

        rect = page.rect
        new_page = out.new_page(width=rect.width, height=rect.height)

        new_page.insert_image(
            rect,
            stream=img_buffer.getvalue()
        )

    output = io.BytesIO()
    out.save(output, garbage=4, deflate=True, clean=True)
    out.close()
    src.close()

    output.seek(0)
    return output.getvalue()


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

    if st.button("Merge & Extreme Compress", type="primary"):
        try:
            with st.spinner("Merging PDFs..."):
                merged_bytes = merge_pdfs(uploaded_files)

            with st.spinner("Extreme compressing..."):
                compressed_bytes = extreme_compress_by_rasterizing(
                    merged_bytes,
                    zoom=0.75,
                    jpeg_quality=80
                )

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
