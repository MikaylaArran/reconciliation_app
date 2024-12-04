import streamlit as st
import pytesseract
from PIL import Image, ImageOps
from pdf2image import convert_from_path
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Ensure Tesseract is installed and accessible

# Predefined account details
ACCOUNT_DETAILS = [
    {"Acc No": "180201", "Acc Description": "Debtors Suspense - Personal expenses made to be refunded to company"},
    {"Acc No": "527001", "Acc Description": "WELFARE - For office expenses like coffee or gifts, team building, etc."},
    {"Acc No": "600001", "Acc Description": "HOTEL MEALS FOREIGN - Hotel and meals for all overseas travel"},
    {"Acc No": "601001", "Acc Description": "OVERSEAS TRAVEL - Flights and transfers"},
    {"Acc No": "602001", "Acc Description": "HOTELS MEALS LOCAL - Local hotel and meal allowances while traveling"},
    {"Acc No": "603001", "Acc Description": "TRAVEL LOCAL - Flights, car hire, Uber, etc."},
    {"Acc No": "604001", "Acc Description": "LOCAL ENTERTAINMENT - Client meetings"},
    {"Acc No": "605001", "Acc Description": "CONFERENCES"},
    {"Acc No": "650001", "Acc Description": "ASSETS LESS THAN R3000"},
    {"Acc No": "750241", "Acc Description": "PRINTING"},
    {"Acc No": "750035", "Acc Description": "GENERAL AIRFREIGHT"},
    {"Acc No": "700035", "Acc Description": "GENERAL POSTAGE"},
    {"Acc No": "700031", "Acc Description": "POSTAGES"},
    {"Acc No": "750491", "Acc Description": "SCHEME PRINTING"},
    {"Acc No": "750194", "Acc Description": "MEMBERSHIP FEES"},
    {"Acc No": "750211", "Acc Description": "PHOTOCOPYING"},
    {"Acc No": "750531", "Acc Description": "STATIONERY"},
    {"Acc No": "750541", "Acc Description": "SUBSCRIPTIONS"},
    {"Acc No": "750005", "Acc Description": "BRANDING COSTS - Branding for corporate gifts ONLY"},
    {"Acc No": "750182", "Acc Description": "PROMOTIONAL ITEMS - Corporate gifts ONLY"},
    {"Acc No": "800091", "Acc Description": "OUT OF SCOPE EXPENSES"},
    {"Acc No": "800141", "Acc Description": "SOFTWARE LICENSES"},
    {"Acc No": "803061", "Acc Description": "PRINTER CONSUMABLES"},
    {"Acc No": "756001", "Acc Description": "CONSULTANCY FEES"},
    {"Acc No": "750031", "Acc Description": "BANK CHARGES - Always for cost of card holder"},
    {"Acc No": "790001", "Acc Description": "INTEREST PAID - OTHER"},
    {"Acc No": "790002", "Acc Description": "INTEREST PAID - BANK"},
    {"Acc No": "470001", "Acc Description": "INTEREST RECEIVED BANK BALANCE"},
    {"Acc No": "470101", "Acc Description": "INTEREST RECEIVED OTHER"},
    {"Acc No": "273111", "Acc Description": "VAT Input - Manual journals"},
]

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

def extract_fields_document(text):
    """Extract key fields from documents dynamically."""
    fields = {}
    try:
        # Extract Company Name (dynamically based on the first few lines of the text)
        text_lines = text.strip().split("\n")
        if len(text_lines) > 0:
            fields["Company Name"] = next(
                (line.strip() for line in text_lines[:3] if line.strip()), "Unknown Company"
            )
        else:
            fields["Company Name"] = "Unknown Company"

        # Extract Total Amount
        total_match = re.search(r"(TOTAL|DUE VAT INCL)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        fields["Total"] = total_match.group(2) if total_match else "Not Found"

        # Extract VAT Amount
        vat_match = re.search(r"(VAT|Vat|vat)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        fields["VAT"] = vat_match.group(2) if vat_match else "Not Found"

        # Extract Date (common date formats)
        date_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        fields["Date"] = date_match.group(1) if date_match else "Not Found"

        # Extract Time (common time formats)
        time_match = re.search(r"\b([01]?[0-9]|2[0-3]):[0-5][0-9](\s?[APap][Mm])?\b", text)
        fields["Time"] = time_match.group(0) if time_match else "Not Found"

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
        safe_value = str(value).encode('ascii', 'ignore').decode('ascii')
        pdf.cell(90, 10, field, 1)
        pdf.cell(100, 10, safe_value, 1, 1)

    pdf_file_path = "extracted_document_data.pdf"
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
st.title("Dynamic Document Processor with Account Dropdown")
st.write("Upload a document (image or PDF) to extract key details and generate a PDF.")

# Account Dropdown
selected_account = st.selectbox(
    "Select an Account",
    [f"{acc['Acc No']} - {acc['Acc Description']}" for acc in ACCOUNT_DETAILS],
)
st.write(f"Selected Account: {selected_account}")

# File Upload
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Handle PDF and Images
    if uploaded_file.name.endswith(".pdf"):
        st.write("Processing PDF...")
        extracted_text = process_pdf(uploaded_file)
    else:
        # Load and process image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Document", use_column_width=True)
        st.write("Preprocessing image...")
        processed_image = preprocess_image(image)
        st.image(processed_image, caption="Preprocessed Image", use_column_width=True)
        extracted_text = extract_text(processed_image)

    st.write("Extracting fields...")
    fields = extract_fields_document(extracted_text)

    st.subheader("Extracted Fields")
    for st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    st.write("Generating PDF...")
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            "Download Extracted Data as PDF",
            pdf_file,
            file_name="extracted_document_data.pdf",
            mime="application/pdf",
        )
else:
    st.write("Please upload a document.")

