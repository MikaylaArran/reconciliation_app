import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance
import pandas as pd
import re

# Configure Tesseract executable path (modify based on your system setup)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update this path if necessary

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

# Helper function to extract monetary amounts from text
def extract_amounts(text):
    # Regular expression to capture monetary values (e.g., "100.00", "R250")
    amounts = re.findall(r'R?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)
    # Clean and standardize amounts (remove "R" and commas, convert to float)
    cleaned_amounts = [float(amount.replace("R", "").replace(",", "")) for amount in amounts]
    return cleaned_amounts

# Helper function to reconcile amounts
def reconcile_amounts(slip_amounts, bank_statement_amounts):
    recon_results = []
    for slip_amount in slip_amounts:
        if slip_amount in bank_statement_amounts:
            recon_results.append({"Slip Amount": slip_amount, "Status": "Match Found"})
        else:
            recon_results.append({"Slip Amount": slip_amount, "Status": "No Match"})
    return pd.DataFrame(recon_results)

# Streamlit app
st.title("Reconciliation App with Amount Matching")
st.write("Upload images of slips and bank statements to match amounts.")

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

    # Extract amounts
    st.write("Extracting monetary amounts...")
    slip_amounts = extract_amounts(slip_text)
    bank_statement_amounts = extract_amounts(bank_statement_text)
    st.write(f"Extracted Slip Amounts: {slip_amounts}")
    st.write(f"Extracted Bank Statement Amounts: {bank_statement_amounts}")

    # Reconcile amounts
    st.write("Reconciling amounts...")
    recon_results_df = reconcile_amounts(slip_amounts, bank_statement_amounts)

    # Display reconciliation results
    st.subheader("Reconciliation Results")
    st.dataframe(recon_results_df)

    # Show summary
    st.subheader("Summary")
    total_slip_amounts = sum(slip_amounts)
    total_matched_amounts = sum(
        amount for amount in slip_amounts if amount in bank_statement_amounts
    )
    st.write(f"Total Slip Amounts: R{total_slip_amounts:.2f}")
    st.write(f"Total Matched Amounts: R{total_matched_amounts:.2f}")
    st.write(
        f"Discrepancies: R{total_slip_amounts - total_matched_amounts:.2f}"
    )

    # Download reconciliation results
    csv = recon_results_df.to_csv(index=False)
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="reconciliation_results.csv",
        mime="text/csv",
    )
