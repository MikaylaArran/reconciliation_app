import streamlit as st
import pytesseract
from PIL import Image, ImageOps
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Ensure Tesseract is installed and accessible

# Account Number and Description Data
account_data = {
    "180201": "Debtors Suspense - Personal expenses made to be refunded to company",
    "527001": "WELFARE - For office expenses like coffee or gifts like flowers/team building functions",
    "600001": "HOTEL MEALS FOREIGN - Hotel and meals for all overseas travel (including Africa)",
    "601001": "OVERSEAS TRAVEL - Flights and transfers",
    "602001": "HOTELS MEALS LOCAL - Local hotel and meal allowances while traveling",
    "603001": "TRAVEL LOCAL - Flights, car hire, Uber, etc.",
    "604001": "LOCAL ENTERTAINMENT - Client meetings",
    "605001": "CONFERENCES",
    "650001": "ASSETS LESS THAN R3000",
    "750241": "PRINTING",
    "750035": "GENERAL AIRFREIGHT",
    "700035": "GENERAL POSTAGE",
    "702001": "GENERAL STATIONERY",
    "703001": "GENERAL COURIER SERVICES",
}

# Combine account numbers and descriptions for dropdown
dropdown_options = [f"{key} - {value}" for key, value in account_data.items()]

# Streamlit App
st.title("Enhanced Document Processor with Account Selection")
st.write("Upload a document to classify, extract fields, and generate a PDF.")

# Dropdown for Account Selection
selected_option = st.selectbox("Select Account", options=dropdown_options)

# Extract selected account number and description
selected_account, selected_description = selected_option.split(" - ", 1)
st.write(f"**Selected Account Number:** {selected_account}")
st.write(f"**Account Description:** {selected_description}")

# OCR and Document Processing
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Load image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)

    st.write("Preprocessing image...")
    processed_image = preprocess_image(image)
    st.image(processed_image, caption="Preprocessed Image", use_column_width=True)

    st.write("Extracting text...")
    extracted_text = extract_text(processed_image)

    # Classify Document
    doc_type = classify_document(extracted_text)
    st.subheader(f"Document Type: {doc_type}")

    # Extract Fields
    st.write("Extracting fields...")
    fields = extract_fields(extracted_text, doc_type)

    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    # Generate PDF
    st.write("Generating PDF...")
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            "Download Extracted Data as PDF",
            pdf_file,
            file_name="extracted_data.pdf",
            mime="application/pdf",
        )
else:
    st.write("Please upload a document.")

# Utility Functions
def extract_text(image):
    """Extract text from the uploaded document."""
    try:
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(image, config=custom_config)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

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
        return image

def classify_document(text):
    """Classify the document based on extracted text."""
    if "account" in text.lower() or "balance" in text.lower():
        return "Bank Statement"
    elif "vat" in text.lower() or "total" in text.lower():
        return "Receipt"
    elif "invoice" in text.lower() or "due" in text.lower():
        return "Invoice"
    else:
        return "Unknown"

def extract_fields(text, doc_type):
    """Extract specific fields based on document type."""
    fields = {}
    try:
        if doc_type == "Receipt":
            fields["Total"] = re.search(r'Total.*?(\d+\.\d{2})', text, re.IGNORECASE).group(1) if re.search(r'Total.*?(\d+\.\d{2})', text, re.IGNORECASE) else "Not Found"
            fields["Tip"] = re.search(r'Tip.*?(\d+\.\d{2})', text, re.IGNORECASE).group(1) if re.search(r'Tip.*?(\d+\.\d{2})', text, re.IGNORECASE) else "Not Found"
            fields["VAT"] = re.search(r'VAT.*?(\d+\.\d{2})', text, re.IGNORECASE).group(1) if re.search(r'VAT.*?(\d+\.\d{2})', text, re.IGNORECASE) else "Not Found"
        else:
            fields["Note"] = "No tailored fields for this document type."
    except Exception as e:
        st.error(f"Error extracting fields: {e}")
    return fields

def generate_pdf(fields):
    """Generate a PDF with the extracted fields."""
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
        pdf.cell(100, 10, value if isinstance(value, str) else ", ".join(value), 1, 1)

    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path
