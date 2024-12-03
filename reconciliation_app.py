import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import re
from fpdf import FPDF  # Library for generating PDFs

# Configure Tesseract executable path
try:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
except FileNotFoundError:
    st.error("Tesseract OCR is not installed. Please install it and ensure the path is configured correctly.")
    st.stop()

# OCR Function
def extract_text(image):
    try:
        return pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

# Field Extraction Function
def extract_fields(text):
    patterns = {
        "Date": r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
        "Invoice Number": r'\bInvoice[:\s]?\d+\b',
        "Total Amount": r'\b(?:\$|R)?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b'
    }
    extracted = {key: re.search(pattern, text).group(0) if re.search(pattern, text) else "Not Found"
                 for key, pattern in patterns.items()}
    return extracted

# PDF Generation Function
def generate_pdf(fields):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Extracted Fields", ln=True, align="C")

    for field, value in fields.items():
        pdf.cell(200, 10, txt=f"{field}: {value}", ln=True, align="L")

    # Save PDF to a temporary file
    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Document Processing with PDF Output")
st.write("Upload a document to extract fields and generate a downloadable PDF.")

# Upload Document
uploaded_file = st.file_uploader("Upload Document", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)

    # OCR Processing
    st.write("Extracting text...")
    extracted_text = extract_text(image)

    # Extract Fields
    st.write("Extracting fields...")
    fields = extract_fields(extracted_text)
    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    # Generate and Download PDF
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            label="Download Extracted Data as PDF",
            data=pdf_file,
            file_name="extracted_data.pdf",
            mime="application/pdf",
        )
