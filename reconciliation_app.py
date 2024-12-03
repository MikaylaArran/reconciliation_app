import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import re
import joblib  # Corrected import for joblib

# Configure Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# Load pre-trained AI models (placeholder paths for now)
# Replace these paths with your actual model files if available
try:
    field_extraction_model = joblib.load("field_extraction_model.pkl")
    document_classifier_model = joblib.load("document_classifier_model.pkl")
except FileNotFoundError:
    field_extraction_model = None
    document_classifier_model = None

# OCR Function
def extract_text(image):
    return pytesseract.image_to_string(image)

# AI-Powered Field Extraction
def ai_extract_fields(text):
    if field_extraction_model:
        input_data = [text]  # Adjust preprocessing based on your model's requirements
        predictions = field_extraction_model.predict(input_data)
        fields = {
            "Date": predictions[0][0],  # Adjust indices based on model output
            "Invoice Number": predictions[0][1],
            "Total Amount": predictions[0][2]
        }
        return fields
    else:
        return {"Date": "AI Model Not Loaded", "Invoice Number": "AI Model Not Loaded", "Total Amount": "AI Model Not Loaded"}

# Document Classification
def classify_document(text):
    if document_classifier_model:
        input_data = [text]  # Adjust preprocessing as needed
        document_type = document_classifier_model.predict(input_data)[0]
        return document_type
    else:
        return "AI Model Not Loaded"

# Reconciliation Function
def reconcile_data(slip_text, bank_statement_text):
    slips = [line.strip() for line in slip_text.splitlines() if line.strip()]
    bank_statements = [line.strip() for line in bank_statement_text.splitlines() if line.strip()]
    
    recon_results = []
    for slip in slips:
        if slip in bank_statements:
            recon_results.append({"Slip Entry": slip, "Status": "Match Found"})
        else:
            recon_results.append({"Slip Entry": slip, "Status": "No Match"})
    return pd.DataFrame(recon_results)

# Streamlit App
st.title("AI-Powered Content Capture and Processing")
st.write("Upload or capture a document to classify and extract fields.")

# Upload Document
uploaded_file = st.file_uploader("Upload Document", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Document", use_column_width=True)

    # OCR Processing
    st.write("Extracting text...")
    extracted_text = extract_text(image)

    # Document Classification
    st.write("Classifying document type...")
    document_type = classify_document(extracted_text)
    st.write(f"**Document Type:** {document_type}")

    # AI-Powered Field Extraction
    st.write("Extracting fields...")
    fields = ai_extract_fields(extracted_text)
    st.subheader("Extracted Fields")
    for field, value in fields.items():
        st.write(f"**{field}:** {value}")

    # Option to Upload Bank Statement for Reconciliation
    uploaded_bank_statement = st.file_uploader("Upload Bank Statement for Reconciliation", type=["jpg", "png", "jpeg"])
    if uploaded_bank_statement:
        bank_statement_image = Image.open(uploaded_bank_statement)
        bank_statement_text = extract_text(bank_statement_image)

        # Reconciliation
        st.write("Reconciling data...")
        recon_results_df = reconcile_data(extracted_text, bank_statement_text)
        st.subheader("Reconciliation Results")
        st.dataframe(recon_results_df)

        # Download Reconciliation Results
        csv = recon_results_df.to_csv(index=False)
        st.download_button(label="Download Results as CSV", data=csv, file_name="reconciliation_results.csv")
