import streamlit as st
import pytesseract
from PIL import Image
import re
from fpdf import FPDF

# Configure Tesseract executable path
try:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Update this path if needed
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
    fields = {}
    try:
        # Store Information
        fields["Store Name"] = re.search(r'Woolworths', text).group(0) if re.search(r'Woolworths', text) else "Not Found"
        fields["Branch"] = re.search(r'Honeycrest Randpark', text).group(0) if re.search(r'Honeycrest Randpark', text) else "Not Found"
        fields["Address"] = re.search(r'Honeycrest Village,.*?\n', text).group(0).strip() if re.search(r'Honeycrest Village,.*?\n', text) else "Not Found"
        
        # Transaction Details
        fields["Date"] = re.search(r'\d{2}/\d{2}/\d{4}', text).group(0) if re.search(r'\d{2}/\d{2}/\d{4}', text) else "Not Found"
        fields["Time"] = re.search(r'\d{2}:\d{2}:\d{2}', text).group(0) if re.search(r'\d{2}:\d{2}:\d{2}', text) else "Not Found"
        fields["Transaction Number"] = re.search(r'Trans\sNo\s(\d+)', text).group(1) if re.search(r'Trans\sNo\s(\d+)', text) else "Not Found"
        
        # Itemized Purchases
        items = re.findall(r'(S RS.*?\d+\.\d+)', text)
        fields["Items"] = items if items else ["Not Found"]
        fields["Total"] = re.search(r'TOTAL.*?(\d+\.\d+)', text).group(1) if re.search(r'TOTAL.*?(\d+\.\d+)', text) else "Not Found"
        
        # Payment Method
        fields["Payment Type"] = re.search(r'Card Mastercard', text).group(0) if re.search(r'Card Mastercard', text) else "Not Found"
        fields["Account Number"] = re.search(r'Account Number.*?(\*\*\*\*\s\d+)', text).group(1) if re.search(r'Account Number.*?(\*\*\*\*\s\d+)', text) else "Not Found"
        
        # VAT Summary
        fields["Gross"] = re.search(r'Gross.*?(\d+\.\d+)', text).group(1) if re.search(r'Gross.*?(\d+\.\d+)', text) else "Not Found"
        fields["VAT Amount"] = re.search(r'VAT.*?(\d+\.\d+)', text).group(1) if re.search(r'VAT.*?(\d+\.\d+)', text) else "Not Found"
        fields["Net"] = re.search(r'Net.*?(\d+\.\d+)', text).group(1) if re.search(r'Net.*?(\d+\.\d+)', text) else "Not Found"
        
        # Return Policy
        fields["Refund Deadline"] = re.search(r'LAST DAY FOR FULL REFUND IS\s(\d{2}/\d{2}/\d{4})', text).group(1) if re.search(r'LAST DAY FOR FULL REFUND IS\s(\d{2}/\d{2}/\d{4})', text) else "Not Found"
        
    except Exception as e:
        st.error(f"Error extracting fields: {e}")
    
    return fields

# PDF Generation Function
def generate_pdf(fields):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Extracted Fields", ln=True, align="C")

    for field, value in fields.items():
        if isinstance(value, list):
            pdf.cell(200, 10, txt=f"{field}: {', '.join(value)}", ln=True, align="L")
        else:
            pdf.cell(200, 10, txt=f"{field}: {value}", ln=True, align="L")

    # Save PDF to a temporary file
    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Slip Data Extraction and PDF Generator")
st.write("Upload a slip to extract detailed fields and generate a downloadable PDF.")

# Upload Slip
uploaded_file = st.file_uploader("Upload Slip", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # Display uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Slip", use_column_width=True)

    # Perform OCR
    st.write("Extracting text...")
    extracted_text = extract_text(image)

    # Extract fields
    st.write("Extracting fields...")
    fields = extract_fields(extracted_text)

    # Display extracted fields
    st.subheader("Extracted Fields")
    for field, value in fields.items():
        if isinstance(value, list):
            st.write(f"**{field}:** {', '.join(value)}")
        else:
            st.write(f"**{field}:** {value}")

    # Generate and Download PDF
    st.write("Generating PDF...")
    pdf_file_path = generate_pdf(fields)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            label="Download Extracted Data as PDF",
            data=pdf_file,
            file_name="extracted_data.pdf",
            mime="application/pdf",
        )
else:
    st.write("Please upload a slip to extract information.")
