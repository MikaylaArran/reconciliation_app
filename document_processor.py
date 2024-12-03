import streamlit as st
import pytesseract
from PIL import Image, ImageOps
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Update if necessary

# OCR Function
def extract_text(image):
    try:
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(image, config=custom_config)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

# Preprocess Image
def preprocess_image(image):
    try:
        # Convert to RGB and resize
        image = image.convert("RGB")
        base_width = 1000
        w_percent = base_width / float(image.size[0])
        h_size = int(float(image.size[1]) * w_percent)
        resized_image = image.resize((base_width, h_size))

        # Convert to grayscale and binarize
        grayscale_image = ImageOps.grayscale(resized_image)
        binary_image = grayscale_image.point(lambda x: 0 if x < 128 else 255, '1')
        return binary_image
    except Exception as e:
        st.error(f"Error during preprocessing: {e}")
        return image

# Document Classifier
def classify_document(text):
    if "account" in text.lower() or "balance" in text.lower():
        return "Bank Statement"
    elif "vat" in text.lower() or "total" in text.lower():
        return "Receipt"
    elif "invoice" in text.lower() or "due" in text.lower():
        return "Invoice"
    else:
        return "Unknown"

# Field Extraction
def extract_fields(text, doc_type):
    fields = {}
    try:
        if doc_type == "Receipt":
            fields["Store Name"] = re.search(r'(Woolworths|Checkers|Spar|Shoprite)', text, re.IGNORECASE).group(0) if re.search(r'(Woolworths|Checkers|Spar|Shoprite)', text, re.IGNORECASE) else "Not Found"
            fields["Date"] = re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text).group(0) if re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text) else "Not Found"
            fields["Total"] = re.search(r'Total.*?(\d+\.\d{2})', text, re.IGNORECASE).group(1) if re.search(r'Total.*?(\d+\.\d{2})', text, re.IGNORECASE) else "Not Found"
            fields["VAT Amount"] = re.search(r'VAT.*?(\d+\.\d{2})', text, re.IGNORECASE).group(1) if re.search(r'VAT.*?(\d+\.\d{2})', text, re.IGNORECASE) else "Not Found"
        elif doc_type == "Bank Statement":
            fields["Bank Name"] = re.search(r'(FNB|Capitec|Absa|Standard Bank|Nedbank)', text, re.IGNORECASE).group(0) if re.search(r'(FNB|Capitec|Absa|Standard Bank|Nedbank)', text, re.IGNORECASE) else "Not Found"
            fields["Account Number"] = re.search(r'Account Number.*?(\d{4}[- ]\d{4}[- ]\d{4})', text).group(1) if re.search(r'Account Number.*?(\d{4}[- ]\d{4}[- ]\d{4})', text) else "Not Found"
            fields["Balance"] = re.search(r'Balance.*?(\d+\.\d{2})', text).group(1) if re.search(r'Balance.*?(\d+\.\d{2})', text) else "Not Found"
            fields["Transaction Date"] = re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text).group(0) if re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text) else "Not Found"
        elif doc_type == "Invoice":
            fields["Invoice Number"] = re.search(r'Invoice Number.*?(\d+)', text).group(1) if re.search(r'Invoice Number.*?(\d+)', text) else "Not Found"
            fields["Due Date"] = re.search(r'Due Date.*?(\d{2}[/-]\d{2}[/-]\d{4})', text).group(1) if re.search(r'Due Date.*?(\d{2}[/-]\d{2}[/-]\d{4})', text) else "Not Found"
            fields["Total Amount"] = re.search(r'Total.*?(\d+\.\d{2})', text).group(1) if re.search(r'Total.*?(\d+\.\d{2})', text) else "Not Found"
        else:
            fields["Note"] = "Document type not recognized for tailored field extraction."
    except Exception as e:
        st.error(f"Error extracting fields: {e}")
    return fields

# PDF Generation
def generate_pdf(fields):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Extracted Document Data", ln=True, align="C")
    pdf.ln(10)

    # Fields Table
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(90, 10, "Field", 1, 0, "C", fill=True)
    pdf.cell(100, 10, "Value", 1, 1, "C", fill=True)

    for field, value in fields.items():
        pdf.cell(90, 10, field, 1)
        pdf.cell(100, 10, value if len(value) <= 100 else value[:97] + "...", 1, 1)

    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Universal Document Processor")
st.write("Upload any document to classify, extract fields, and generate a PDF.")

# File Upload
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Display uploaded document
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)

    # Preprocess and OCR
    st.write("Preprocessing image...")
    processed_image = preprocess_image(image)
    st.image(processed_image, caption="Preprocessed Image", use_column_width=True)

    st.write("Extracting text...")
    extracted_text = extract_text(processed_image)

    # Document Classification
    st.write("Classifying document type...")
    doc_type = classify_document(extracted_text)
    st.subheader(f"Document Type: {doc_type}")

    # Field Extraction
    st.write("Extracting fields...")
    fields = extract_fields(extracted_text, doc_type)

    # Display Fields
    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    # Generate PDF
    st.write("Generating PDF...")
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button("Download Extracted Data as PDF", pdf_file, "extracted_data.pdf", "application/pdf")
else:
    st.write("Please upload a document.")
