import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import joblib  # For loading the trained ML model
from fpdf import FPDF

# Configure Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Update this if needed

# Load pre-trained field extraction model
try:
    field_extraction_model = joblib.load("field_extraction_model.pkl")  # Placeholder for your trained model
except FileNotFoundError:
    field_extraction_model = None
    st.warning("Field extraction model not found. Default patterns will be used.")

# OCR Function
def extract_text(image):
    return pytesseract.image_to_string(image)

# Dynamic Field Extraction Function
def extract_fields(text):
    if field_extraction_model:
        # Use the ML model to predict fields dynamically
        predictions = field_extraction_model.predict([text])
        fields = predictions[0]  # Assume the model outputs a dictionary of fields
    else:
        # Default field extraction using regex as a fallback
        fields = {
            "Date": re.search(r'\b(?:\d{2}/\d{2}/\d{4})\b', text).group(0) if re.search(r'\b(?:\d{2}/\d{2}/\d{4})\b', text) else "Not Found",
            "Total": re.search(r'TOTAL.*?(\d+\.\d+)', text).group(1) if re.search(r'TOTAL.*?(\d+\.\d+)', text) else "Not Found",
            "VAT Amount": re.search(r'VAT.*?(\d+\.\d+)', text).group(1) if re.search(r'VAT.*?(\d+\.\d+)', text) else "Not Found",
        }
    return fields

# PDF Generation Function
def generate_pdf(fields):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Extracted Fields", ln=True, align="C")

    for field, value in fields.items():
        pdf.cell(200, 10, txt=f"{field}: {value}", ln=True, align="L")

    # Save PDF to a temporary file
    pdf_file_path = "extracted_data.pdf"
    pdf.output(pdf_file_path)
    return pdf_file_path

# Streamlit App
st.title("AI-Powered Slip Processing with Learning")
st.write("Upload a slip to extract fields and generate a PDF. Provide corrections to improve accuracy over time.")

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
    user_feedback = {}
    for field, value in fields.items():
        user_feedback[field] = st.text_input(f"**{field}:**", value)

    # Generate and Download PDF
    if st.button("Generate PDF"):
        st.write("Generating PDF...")
        pdf_file_path = generate_pdf(user_feedback)
        with open(pdf_file_path, "rb") as pdf_file:
            st.download_button(
                label="Download Extracted Data as PDF",
                data=pdf_file,
                file_name="extracted_data.pdf",
                mime="application/pdf",
            )

    # Save Feedback for Learning
    if st.button("Submit Feedback"):
        feedback_data = {"text": extracted_text, "fields": user_feedback}
        with open("feedback.csv", "a") as f:
            f.write(f"{feedback_data}\n")
        st.success("Feedback submitted. This will help improve the model!")
else:
    st.write("Please upload a slip to extract information.")
