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
        custom_config = r'--oem 3 --psm 6'  # Custom Tesseract config for better accuracy
        return pytesseract.image_to_string(image, config=custom_config)
    except Exception as e:
        st.error(f"Error during OCR: {e}")
        return ""

# Preprocess Image
def preprocess_image(image):
    try:
        # Ensure the image is in RGB mode
        image = image.convert("RGB")

        # Resize the image for OCR, maintaining aspect ratio
        base_width = 1000
        w_percent = base_width / float(image.size[0])
        h_size = int((float(image.size[1]) * float(w_percent)))
        resized_image = image.resize((base_width, h_size))

        # Convert to grayscale
        grayscale_image = ImageOps.grayscale(resized_image)

        # Apply thresholding (binarization)
        binary_image = grayscale_image.point(lambda x: 0 if x < 128 else 255, '1')

        return binary_image
    except Exception as e:
        st.error(f"Error during preprocessing: {e}")
        return image

# Field Extraction Function
def extract_fields(text):
    fields = {}
    try:
        # Extract commonly found fields
        fields["Store/Institution Name"] = re.search(r'(Woolworths|Checkers|FNB|Capitec|Absa|Standard Bank)', text, re.IGNORECASE).group(0) if re.search(r'(Woolworths|Checkers|FNB|Capitec|Absa|Standard Bank)', text, re.IGNORECASE) else "Not Found"
        fields["Date"] = re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text).group(0) if re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text) else "Not Found"
        fields["Transaction Amount"] = re.search(r'(Amount|Total|Balance|Debit|Credit).*?(\d+\.\d{2})', text).group(2) if re.search(r'(Amount|Total|Balance|Debit|Credit).*?(\d+\.\d{2})', text) else "Not Found"
        fields["Account Number"] = re.search(r'Account Number.*?(\d{4}[- ]\d{4}[- ]\d{4})', text).group(1) if re.search(r'Account Number.*?(\d{4}[- ]\d{4}[- ]\d{4})', text) else "Not Found"
        fields["Transaction/Reference Number"] = re.search(r'(Transaction|Reference|Trans|Invoice) No.*?(\d+)', text).group(2) if re.search(r'(Transaction|Reference|Trans|Invoice) No.*?(\d+)', text) else "Not Found"
        fields["Time"] = re.search(r'\b\d{2}:\d{2}(:\d{2})?\b', text).group(0) if re.search(r'\b\d{2}:\d{2}(:\d{2})?\b', text) else "Not Found"

    except Exception as e:
        st.error(f"Error extracting fields: {e}")

    return fields

# PDF Generation Function
def generate_pdf(fields, logo_path=None):
    pdf = FPDF()
    pdf.add_page()

    # Add Logo (only if the path exists)
    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)
        pdf.ln(20)  # Add spacing below the logo

    # Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Extracted Document Data", ln=True, align="C")
    pdf.ln(10)

    # Add Fields in Table Format
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(90, 10, "Field", 1, 0, "C", fill=True)
    pdf.cell(100, 10, "Value", 1, 1, "C", fill=True)

    for field, value in fields.items():
        pdf.cell(90, 10, field, 1)
        if isinstance(value, list):
            wrapped_text = ", ".join(value)[:90]  # Truncate text to fit
            pdf.cell(100, 10, wrapped_text, 1, 1)
        else:
            wrapped_text = str(value)[:90]  # Truncate text to fit
            pdf.cell(100, 10, wrapped_text, 1, 1)

    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Universal Document Processor")
st.write("Upload any document to extract fields and generate a PDF.")

# Upload Document
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])
logo_path = "logo.png"  # Ensure your logo file exists in the same directory

if uploaded_file:
    # Display uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)

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
    st.write("Please upload a document.")
