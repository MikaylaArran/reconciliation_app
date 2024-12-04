import streamlit as st
import pytesseract
from PIL import Image, ImageOps
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"

# Predefined account details
ACCOUNT_DETAILS = [
    {"Acc No": "180201", "Acc Description": "Debtors Suspense - Personal expenses made to be refunded to company"},
    {"Acc No": "527001", "Acc Description": "WELFARE - For office expenses like coffee or gifts, team building, etc."},
    # Add more accounts as needed...
]

# Synonyms for common fields to handle different terminologies
FIELD_SYNONYMS = {
    "subtotal": ["sub total", "net amount", "amount"],
    "total": ["total", "amount due", "balance due"],
    "taxable_value": ["taxable val", "taxable amount", "taxable"],
    "vat": ["vat", "tax", "vat amount"],
    "date": ["date", "transaction date", "invoice date"],
    "time": ["time", "transaction time"]
}

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

def find_value_after_label(lines, label_patterns):
    """Find the value that appears after a given label in the text lines."""
    for i, line in enumerate(lines):
        for pattern in label_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Check the same line for a value
                value_match = re.search(r"([\d,]+\.\d{2})", line)
                if value_match:
                    return value_match.group(1)
                # Check the next line for a value
                elif i + 1 < len(lines):
                    next_line_match = re.search(r"([\d,]+\.\d{2})", lines[i + 1])
                    if next_line_match:
                        return next_line_match.group(1)
    return "Not Found"

def extract_fields_document(text):
    """Extract key fields from documents dynamically."""
    fields = {}
    lines = text.split("\n")

    # Extract Company Name (assumed to be in the first few lines)
    fields["Company Name"] = next((line.strip() for line in lines[:3] if line.strip()), "Unknown Company")

    # Extract fields based on synonyms
    for field, synonyms in FIELD_SYNONYMS.items():
        label_patterns = [re.escape(synonym) for synonym in synonyms]
        value = find_value_after_label(lines, label_patterns)
        fields[field.replace("_", " ").title()] = value

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
st.title("Dynamic Document Processor with Flexible Field Extraction")

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
