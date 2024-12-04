import streamlit as st
import pytesseract
from PIL import Image, ImageOps
from pdf2image import convert_from_path
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Ensure Tesseract is installed and accessible

def preprocess_image(image):
    """Preprocess the uploaded image for OCR."""
    try:
        image = image.convert("RGB")
        base_width = 1000
        w_percent = base_width / float(image.size[0])
        h_size = int((float(image.size[1]) * float(w_percent)))
        resized_image = image.resize((base_width, h_size))

        grayscale_image = ImageOps.grayscale(resized_image)
        binary_image = grayscale_image.point(lambda x: 0 if x < 128 else 255, '1')
        return binary_image
    except Exception as e:
        st.error(f"Error during preprocessing: {e}")
        return image  # Return the original image if preprocessing fails

def extract_text(image):
    """Extract text from the uploaded document."""
    try:
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(image, config=custom_config)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

def extract_fields_sa_receipt(text):
    """Extract key fields from South African receipts dynamically."""
    fields = {}
    try:
        # Extract Store Name (dynamically based on the first few lines of the text)
        text_lines = text.strip().split("\n")
        fields["Store Name"] = text_lines[0] if len(text_lines) > 0 else "Unknown Store"

        # Extract Total Amount
        total_match = re.search(r"(TOTAL|DUE VAT INCL)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        fields["Total"] = total_match.group(2) if total_match else "Not Found"

        # Extract VAT Amount
        vat_match = re.search(r"VAT VAL[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        fields["VAT"] = vat_match.group(1) if vat_match else "Not Found"

        # Extract Taxable Value
        taxable_match = re.search(r"TAXABLE VAL[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        fields["Taxable Value"] = taxable_match.group(1) if taxable_match else "Not Found"

    except Exception as e:
        st.error(f"Error extracting fields: {e}")
    return fields

def generate_pdf(fields):
    """Generate a PDF with the extracted fields."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Extracted Receipt Data", ln=True, align="C")
    pdf.ln(10)

    # Fields Table
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(90, 10, "Field", 1, 0, "C", fill=True)
    pdf.cell(100, 10, "Value", 1, 1, "C", fill=True)

    for field, value in fields.items():
        pdf.cell(90, 10, field, 1)
        pdf.cell(100, 10, value if isinstance(value, str) else ", ".join(value), 1, 1)

    pdf_file_path = "extracted_receipt_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

def process_pdf(uploaded_pdf):
    """Convert PDF to images and extract text from all pages."""
    try:
        pages = convert_from_path(uploaded_pdf, dpi=300)
        full_text = ""
        for page_number, page in enumerate(pages, start=1):
            st.image(page, caption=f"Page {page_number}", use_column_width=True)
            processed_image = preprocess_image(page)
            page_text = extract_text(processed_image)
            full_text += f"\n--- Page {page_number} ---\n{page_text}"
        return full_text
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return ""

# Streamlit App
st.title("South African Receipt Processor (Dynamic Store Name)")
st.write("Upload a South African receipt (image or PDF) to extract key details and generate a PDF.")

# File Upload
uploaded_file = st.file_uploader("Upload Receipt (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Handle PDF and Images
    if uploaded_file.name.endswith(".pdf"):
        st.write("Processing PDF...")
        extracted_text = process_pdf(uploaded_file)
    else:
        # Load and process image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Receipt", use_column_width=True)
        st.write("Preprocessing image...")
        processed_image = preprocess_image(image)
        st.image(processed_image, caption="Preprocessed Image", use_column_width=True)
        extracted_text = extract_text(processed_image)

    st.write("Extracting fields...")
    fields = extract_fields_sa_receipt(extracted_text)

    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    st.write("Generating PDF...")
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            "Download Extracted Data as PDF",
            pdf_file,
            file_name="extracted_receipt_data.pdf",
            mime="application/pdf",
        )
else:
    st.write("Please upload a receipt.")
