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
    {"Acc No": "750035", "Acc Description": "GENERAL AIRFREIGHT"},
    {"Acc No": "700035", "Acc Description": "GENERAL POSTAGE"},
    {"Acc No": "273111", "Acc Description": "VAT Input - Manual journals"},
    # Add more accounts as needed
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

def extract_vat_details(text):
    """Extract VAT-related values from the text."""
    vat_details = {"Taxable Value": "Not Found", "VAT Value": "Not Found", "Zero-Rated VAT": "Not Found", "Total VAT": "Not Found"}
    try:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            # Look for VAT-related keywords and extract nearby values
            if re.search(r"(Taxable Val|VAT Val|Zero-Rated|VAT|TAX)", line, re.IGNORECASE):
                # Match for amounts in the same line or next line
                taxable_match = re.search(r"(Taxable Val|Taxable).*?([\d,]+\.\d{2})", line, re.IGNORECASE)
                vat_value_match = re.search(r"(VAT Val|Value).*?([\d,]+\.\d{2})", line, re.IGNORECASE)
                zero_rated_match = re.search(r"(Zero-Rated|Zero Rated).*?([\d,]+\.\d{2})", line, re.IGNORECASE)
                general_vat_match = re.search(r"(VAT|Tax).*?([\d,]+\.\d{2})", line, re.IGNORECASE)
                next_line_match = re.search(r"([\d,]+\.\d{2})", lines[i + 1]) if i + 1 < len(lines) else None

                # Populate VAT details based on matches
                if taxable_match:
                    vat_details["Taxable Value"] = taxable_match.group(2)
                if vat_value_match:
                    vat_details["VAT Value"] = vat_value_match.group(2)
                if zero_rated_match:
                    vat_details["Zero-Rated VAT"] = zero_rated_match.group(2)
                if general_vat_match:
                    vat_details["Total VAT"] = general_vat_match.group(2)
                elif next_line_match:
                    vat_details["Total VAT"] = next_line_match.group(1)

    except Exception as e:
        st.error(f"Error extracting VAT details: {e}")
    return vat_details

def extract_fields_document(text):
    """Extract key fields from documents dynamically."""
    fields = {}
    try:
        # Extract Company Name (based on the first few lines of the text)
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

        # Extract Subtotal
        subtotal_match = re.search(r"(SUBTOTAL|Subtotal)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        subtotal = float(subtotal_match.group(2).replace(",", "")) if subtotal_match else None
        fields["Subtotal"] = f"{subtotal:.2f}" if subtotal else "Not Found"

        # Extract VAT details
        vat_details = extract_vat_details(text)
        fields.update(vat_details)

        # Extract Date
        date_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        fields["Date"] = date_match.group(1) if date_match else "Not Found"

        # Extract Time
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

# Streamlit App
st.title("Dynamic Document Processor with Advanced VAT Handling")

# Account Dropdown
selected_account = st.selectbox(
    "Select an Account",
    [f"{acc['Acc No']} - {acc['Acc Description']}" for acc in ACCOUNT_DETAILS],
)
st.write(f"Selected Account: {selected_account}")

# File Upload
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Load and process the image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)
    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)

    # Extract fields and display them
    st.subheader("Extracted Fields")
    fields = extract_fields_document(extracted_text)
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

        # Generate and download PDF
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

