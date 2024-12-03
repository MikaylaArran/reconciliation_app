import streamlit as st
import pytesseract
from PIL import Image, ImageOps
import re
from fpdf import FPDF
import os
import json

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Update if necessary

# Path for the training file
TRAINING_FILE = "field_training.json"

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
        # Use patterns from the training file if available
        trained_patterns = load_training_data()

        for field, pattern in trained_patterns.items():
            match = re.search(pattern, text)
            fields[field] = match.group(0) if match else "Not Found"

        # Default patterns if no trained data exists
        if not fields:
            fields["Store/Institution Name"] = re.search(r'(Woolworths|Checkers|FNB|Capitec|Absa)', text, re.IGNORECASE).group(0) if re.search(r'(Woolworths|Checkers|FNB|Capitec|Absa)', text, re.IGNORECASE) else "Not Found"
            fields["Date"] = re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text).group(0) if re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', text) else "Not Found"
            fields["Transaction Amount"] = re.search(r'(Amount|Total|Balance|Debit|Credit).*?(\d+\.\d{2})', text).group(1) if re.search(r'(Amount|Total|Balance|Debit|Credit).*?(\d+\.\d{2})', text) else "Not Found"

    except Exception as e:
        st.error(f"Error extracting fields: {e}")

    return fields

# Machine Learning: Save Training Data
def save_training_data(field_name, pattern):
    training_data = load_training_data()
    training_data[field_name] = pattern
    with open(TRAINING_FILE, "w") as f:
        json.dump(training_data, f)

# Machine Learning: Load Training Data
def load_training_data():
    if os.path.exists(TRAINING_FILE):
        with open(TRAINING_FILE, "r") as f:
            return json.load(f)
    return {}

# PDF Generation Function
def generate_pdf(fields, logo_path):
    pdf = FPDF()
    pdf.add_page()

    # Add Logo
    if os.path.exists(logo_path):
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
        pdf.multi_cell(100, 10, str(value), 1)

    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("Universal Document Processor with Learning")
st.write("Upload any document to extract fields, generate a PDF, and improve field extraction with AI.")

# Upload Document
uploaded_file = st.file_uploader("Upload Document (JPG, PNG, PDF)", type=["jpg", "png", "jpeg", "pdf"])
logo_path = "logo.png"  # Path to the logo file (ensure it's in the same directory)

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

    # Machine Learning: Allow User to Correct Fields
    st.write("Help us improve field extraction!")
    corrected_fields = {}
    for field, value in fields.items():
        corrected_fields[field] = st.text_input(f"Correct '{field}':", value)

    if st.button("Save Training Data"):
        for field, corrected_value in corrected_fields.items():
            if corrected_value != fields[field]:
                pattern = st.text_input(f"Provide regex pattern for '{field}':", "")
                if pattern:
                    save_training_data(field, pattern)
                    st.success(f"Training data saved for '{field}'!")
else:
    st.write("Please upload a document.")
