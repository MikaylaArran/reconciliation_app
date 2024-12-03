import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd

# Configure Tesseract executable path (modify based on your system setup)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update for your system

def extract_text_from_image(image):
    try:
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"Error processing image: {e}"

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

# Streamlit app
st.title("Reconciliation App")
st.write("Upload images of slips and bank statements for reconciliation.")

# Upload images
slip_image = st.file_uploader("Upload Slip Image", type=["jpg", "png", "jpeg"])
bank_statement_image = st.file_uploader("Upload Bank Statement Image", type=["jpg", "png", "jpeg"])

if slip_image and bank_statement_image:
    # Display uploaded images
    st.image(slip_image, caption="Slip Image", use_column_width=True)
    st.image(bank_statement_image, caption="Bank Statement Image", use_column_width=True)
    
   
