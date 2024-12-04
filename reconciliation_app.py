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
    if "account" in text.lower() or "balance" in text.lower():
        return "Bank Statement"
    elif "vat" in text.lower() or "total" in text.lower():
        return "Receipt"
    elif "invoice" in text.lower() or "due" in text.lower():
        return "Invoice"
    else:
        return "Unknown"

def extract_fields(text):
    """Extract specific fields with a focus on Total, Tip, and VAT."""
    fields = {}
    try:
        # Extract Total
        total_match = re.search(r'(Total|TOTAL|total)[^\d]*([\d,]+\.\d{2})', text)
        fields["Total"] = total_match.group(2) if total_match else "Not Found"

        # Extract Tip
        tip_match = re.search(r'(Tip|TIP|tip)[^\d]*([\d,]+\.\d{2})', text)
        fields["Tip"] = tip_match.group(2) if tip_match else "Not Found"

        # Extract VAT
        vat_match = re.search(r'(VAT|Vat|vat|V\.A\.T\.|V\.A\.T)[^\d]*([\d,]+\.\d{2})', text)
        if vat_match:
            fields["VAT"] = vat_match.group(2)
        else:
            # Try calculating VAT if Total and Subtotal exist
            subtotal_match = re.search(r'(Subtotal|SUBTOTAL|subtotal)[^\d]*([\d,]+\.\d{2})', text)
            if subtotal_match and total_match:
                subtotal = float(subtotal_match.group(2).replace(",", ""))
                total = float(total_match.group(2).replace(",", ""))
                fields["VAT"] = f"{total - subtotal:.2f}" if total > subtotal else "Not Found"
            else:
                fields["VAT"] = "Not Found"

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
st.title("Enhanced Document Processor with Focus on Total, Tip, and VAT")
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
    fields = extract_fields(extracted_text)

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
