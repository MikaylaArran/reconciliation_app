import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance
import pandas as pd

# Configure Tesseract executable path (modify based on your system setup)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update for your system

# Helper function to preprocess images
def preprocess_image(image):
    try:
        grayscale_image = image.convert("L")  # Convert to grayscale
        enhancer = ImageEnhance.Contrast(grayscale_image)
        enhanced_image = enhancer.enhance(2.0)  # Enhance contrast
        return enhanced_image
    except Exception as e:
        st.write(f"Error during preprocessing: {e}")
        return image

# Helper function to extract text from images
def extract_text_from_image(image):
    try:
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        st.write(f"Error during OCR: {e}")
        return ""

# Helper function to reconcile data
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
    st.write("Images uploaded successfully!")

    # Preprocess and display images
    st.write("Preprocessing images...")
    slip_image_processed = preprocess_image(Image.open(slip_image))
    bank_statement_image_processed = preprocess_image(Image.open(bank_statement_image))
    st.image(slip_image_processed, caption="Processed Slip Image", use_column_width=True)
    st.image(bank_statement_image_processed, caption="Processed Bank Statement Image", use_column_width=True)

    # Perform OCR
    st.write("Performing OCR...")
    slip_text = extract_text_from_image(slip_image_processed)
    bank_statement_text = extract_text_from_image(bank_statement_image_processed)

    # Reconcile
    st.write("Reconciling data...")
    recon_results_df = reconcile_data(slip_text, bank_statement_text)

    # Display reconciliation results
    st.subheader("Reconciliation Results")
    st.dataframe(recon_results_df)

    # Download results
    csv = recon_results_df.to_csv(index=False)
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="reconciliation_results.csv",
        mime="text/csv",
    )
