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
    # Add remaining account details here...
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

        # Extract Subtotal
        subtotal_match = re.search(r"(SUBTOTAL|Subtotal)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        subtotal = float(subtotal_match.group(2).replace(",", "")) if subtotal_match else None
        fields["Subtotal"] = f"{subtotal:.2f}" if subtotal else "Not Found"

        # Extract Taxable VAT
        taxable_vat_match = re.search(r"(TAXABLE VAT|Taxable VAT|Taxable)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        taxable_vat = float(taxable_vat_match.group(2).replace(",", "")) if taxable_vat_match else None
        fields["Taxable VAT"] = f"{taxable_vat:.2f}" if taxable_vat else "Not Found"

        # Extract VAT Value
        vat_value_match = re.search(r"(VAT VALUE|Vat Value|Value Added Tax)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        vat_value = float(vat_value_match.group(2).replace(",", "")) if vat_value_match else None
        fields["VAT Value"] = f"{vat_value:.2f}" if vat_value else "Not Found"

        # Extract VAT Amount
        vat_match = re.search(r"(VAT|Vat|vat|TAX|Tax|tax)[^\d]*([\d,]+\.\d{2})", text, re.IGNORECASE)
        vat_amount = float(vat_match.group(2).replace(",", "")) if vat_match else None

        # Extract VAT Percentage
        vat_percentage_match = re.search(r"(VAT|Vat|vat|Tax).*?(\d{1,2})%", text, re.IGNORECASE)
        vat_percentage = int(vat_percentage_match.group(2)) if vat_percentage_match else None

        # Compute VAT if necessary
        if not vat_amount and subtotal and vat_percentage:
            vat_amount = (subtotal * vat_percentage) / 100
        elif not vat_amount and subtotal and fields["Total"] != "Not Found":
            total = float(fields["Total"].replace(",", ""))
            vat_amount = total - subtotal

        fields["VAT"] = f"{vat_amount:.2f}" if vat_amount else "Not Found"

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

# Streamlit App
st.title("Dynamic Document Processor")

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
