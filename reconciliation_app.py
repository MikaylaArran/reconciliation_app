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
        return pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

# Preprocess Image
def preprocess_image(image):
    # Convert to grayscale
    grayscale_image = ImageOps.grayscale(image)
    # Apply thresholding (binarization)
    binary_image = grayscale_image.point(lambda x: 0 if x < 128 else 255, '1')
    return binary_image

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
def generate_pdf(fields, logo_path):
    pdf = FPDF()
    pdf.add_page()
    
    # Add Logo
    pdf.image(logo_path, x=10, y=8, w=30)  # Adjust as needed for position/size
    
    # Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Extracted Slip Data", ln=True, align="C")
    pdf.ln(10)  # Add some vertical spacing

    # Add Fields in Table Format
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 220, 255)  # Light blue for table header background
    pdf.cell(90, 10, "Field", 1, 0, "C", fill=True)
    pdf.cell(100, 10, "Value", 1, 1, "C", fill=True)

    for field, value in fields.items():
        pdf.cell(90, 10, field, 1)
        if isinstance(value, list):
            pdf.cell(100, 10, ", ".join(value), 1, 1)
        else:
            pdf.cell(100, 10, value, 1, 1)

    # Save PDF to a temporary file
    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Slip Data Extraction and PDF Generator")
st.write("Upload a slip to extract fields and generate a PDF.")

# Upload Slip
uploaded_file = st.file_uploader("Upload Slip", type=["jpg", "png", "jpeg"])
logo_path = "logo-triangle-2.png"  # Ensure this is available in the same directory

if uploaded_file:
    # Display uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Slip", use_column_width=True)

    # Preprocess and Perform OCR
    st.write("Preprocessing image...")
    processed_image = preprocess_image(image)
    st.image(processed_image, caption="Preprocessed Image", use_column_width=True)

    st.write("Extracting text...")
    extracted_text = extract_text(processed_image)

    # Debugging: Display the raw OCR text
    st.subheader("Raw OCR Text")
    st.text(extracted_text)

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
    pdf_file_path = generate_pdf(fields, logo_path)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            label="Download Extracted Data as PDF",
            data=pdf_file,
            file_name="extracted_data.pdf",
            mime="application/pdf",
        )
else:
    st.write("Please upload a slip to extract information.")
