import streamlit as st
import pytesseract
from PIL import Image, ImageOps
import re
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Ensure Tesseract is installed and accessible

# Utility Functions
def preprocess_image(image):
    """Preprocess the uploaded image for OCR."""
    try:
        image = image.convert("RGB")  # Ensure the image is in RGB mode
        base_width = 1000
        w_percent = base_width / float(image.size[0])
        h_size = int((float(image.size[1]) * float(w_percent)))
        resized_image = image.resize((base_width, h_size))  # Resize image

        grayscale_image = ImageOps.grayscale(resized_image)  # Convert to grayscale
        binary_image = grayscale_image.point(lambda x: 0 if x < 128 else 255, '1')  # Threshold
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

def classify_document(text):
    """Classify the document based on extracted text."""
    text_lower = text.lower()
    if "account" in text_lower or "balance" in text_lower or "branch" in text_lower:
        return "Bank Statement"
    elif "vat" in text_lower or "total" in text_lower or "tip" in text_lower:
        return "Slip/Invoice"
    elif "invoice" in text_lower or "due" in text_lower:
        return "Invoice"
    else:
        return "Unknown"

def extract_fields_sa(text, doc_type):
    """Extract fields tailored for South African slips, invoices, and bank statements."""
    fields = {}
    try:
        if doc_type == "Slip/Invoice":
            # Extract Store Name (common SA stores)
            store_match = re.search(
                r"(Woolworths|Checkers|Pick n Pay|Spar|Shoprite|Clicks|Dis-Chem)",
                text,
                re.IGNORECASE,
            )
            fields["Store Name"] = store_match.group(0) if store_match else "Unknown Store"

            # Extract Date
            date_match = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text)
            fields["Date"] = date_match.group(0) if date_match else "Not Found"

            # Extract Total
            total_match = re.search(r"(Total|TOTAL|total)[^\d]*([\d,]+\.\d{2})", text)
            fields["Total"] = total_match.group(2) if total_match else "Not Found"

            # Extract Tip
            tip_match = re.search(r"(Tip|TIP|tip)[^\d]*([\d,]+\.\d{2})", text)
            fields["Tip"] = tip_match.group(2) if tip_match else "Not Found"

            # Extract VAT
            vat_match = re.search(r"(VAT|Vat|vat)[^\d]*([\d,]+\.\d{2})", text)
            fields["VAT"] = vat_match.group(2) if vat_match else "Not Found"

        elif doc_type == "Bank Statement":
            # Extract Account Number
            acc_number_match = re.search(r"Account Number[^\d]*(\d{10,20})", text)
            fields["Account Number"] = acc_number_match.group(1) if acc_number_match else "Not Found"

            # Extract Branch Code
            branch_code_match = re.search(r"Branch Code[^\d]*(\d{6})", text)
            fields["Branch Code"] = branch_code_match.group(1) if branch_code_match else "Not Found"

            # Extract Transactions
            transactions = re.findall(
                r"(\d{2}[/-]\d{2}[/-]\d{4})[^\d]*(Credit|Debit)[^\d]*(\d+[.,]\d{2})", text, re.IGNORECASE
            )
            fields["Transactions"] = [
                f"{t[0]} - {t[1]}: R{t[2].replace(',', '')}" for t in transactions
            ] if transactions else "No Transactions Found"

        elif doc_type == "Invoice":
            # Extract Invoice Number
            invoice_number_match = re.search(r"Invoice Number[^\d]*(\d+)", text)
            fields["Invoice Number"] = invoice_number_match.group(1) if invoice_number_match else "Not Found"

            # Extract Due Date
            due_date_match = re.search(r"Due Date[^\d]*(\d{2}[/-]\d{2}[/-]\d{4})", text)
            fields["Due Date"] = due_date_match.group(1) if due_date_match else "Not Found"

            # Extract Total Amount
            total_amount_match = re.search(r"(Total|TOTAL|total)[^\d]*([\d,]+\.\d{2})", text)
            fields["Total Amount"] = total_amount_match.group(2) if total_amount_match else "Not Found"

        else:
            fields["Note"] = "Document type not recognized for field extraction."

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

# Streamlit App
st.title("South African Document Processor")
st.write("Upload a document to classify, extract fields, and generate a PDF.")

# File Upload
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

    doc_type = classify_document(extracted_text)
    st.subheader(f"Document Type: {doc_type}")

    st.write("Extracting fields...")
    fields = extract_fields_sa(extracted_text, doc_type)

    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

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
