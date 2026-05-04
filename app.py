import io
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter
import pikepdf


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
st.caption("Upload multiple PDF files, merge them, then download a compressed PDF.")


uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

compression_level = st.selectbox(
    "Compression level",
    [
        "Normal",
        "Strong",
    ],
    index=0
)


def merge_pdfs(files):
    writer = PdfWriter()

    for uploaded_file in files:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            writer.add_page(page)

    merged_bytes = io.BytesIO()
    writer.write(merged_bytes)
    merged_bytes.seek(0)
    return merged_bytes.getvalue()


def compress_pdf(pdf_bytes, strong=False):
    input_pdf = io.BytesIO(pdf_bytes)
    output_pdf = io.BytesIO()

    with pikepdf.open(input_pdf) as pdf:
        pdf.remove_unreferenced_resources()

        save_kwargs = {
            "linearize": True,
            "compress_streams": True,
            "recompress_flate": True,
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        }

        if strong:
            save_kwargs["deterministic_id"] = True

        pdf.save(output_pdf, **save_kwargs)

    output_pdf.seek(0)
    return output_pdf.getvalue()


def size_mb(data):
    return len(data) / 1024 / 1024


if uploaded_files:
    st.subheader("Uploaded files")

    for i, f in enumerate(uploaded_files, start=1):
        st.write(f"{i}. {f.name} - {f.size / 1024 / 1024:.2f} MB")

    output_name = st.text_input(
        "Output filename",
        value="merged_compressed.pdf"
    )

    if not output_name.lower().endswith(".pdf"):
        output_name += ".pdf"

    if st.button("Merge and compress PDF", type="primary"):
        try:
            with st.spinner("Merging PDFs..."):
                merged = merge_pdfs(uploaded_files)

            with st.spinner("Compressing PDF..."):
                compressed = compress_pdf(
                    merged,
                    strong=(compression_level == "Strong")
                )

            st.success("PDF created successfully.")

            c1, c2 = st.columns(2)
            c1.metric("Merged size", f"{size_mb(merged):.2f} MB")
            c2.metric("Compressed size", f"{size_mb(compressed):.2f} MB")

            st.download_button(
                label="Download compressed PDF",
                data=compressed,
                file_name=output_name,
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.info("Upload at least 2 PDF files.")
