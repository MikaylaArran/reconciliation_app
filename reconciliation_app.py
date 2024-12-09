import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import re

# Configure Tesseract path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"

# Preprocess the uploaded image
def preprocess_image(image):
    # Convert to grayscale
    grayscale_image = ImageOps.grayscale(image)

    # Enhance edges and denoise
    enhanced_image = grayscale_image.filter(ImageFilter.EDGE_ENHANCE_MORE)

    # Apply binary thresholding
    binary_image = enhanced_image.point(lambda p: 0 if p < 128 else 255)
    return binary_image

# Extract text using OCR
def extract_text(image):
    ocr_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(image, config=ocr_config)

# Parse receipt text
def parse_receipt_text(text):
    lines = text.split("\n")
    structured_data = {
        "Company Name": None,
        "Date": None,
        "Items": [],
        "Subtotal": None,
        "Tax": None,
        "Total": None
    }

    # Extract company name (assume it’s in the first few lines)
    for line in lines[:3]:
        if line.strip():
            structured_data["Company Name"] = line.strip()
            break

    # Extract date
    date_pattern = r'\d{1,2} [A-Za-z]{3,} \d{4}'
    for line in lines:
        date_match = re.search(date_pattern, line)
        if date_match:
            structured_data["Date"] = date_match.group()
            break

    # Extract items (lines with text and prices)
    item_pattern = r'(.*)\s+(\d+\.\d{2})$'
    for line in lines:
        item_match = re.match(item_pattern, line)
        if item_match:
            item_name = item_match.group(1).strip()
            item_price = float(item_match.group(2))
            structured_data["Items"].append({"Item": item_name, "Price": item_price})

    # Extract subtotal, tax, and total using synonyms
    field_patterns = {
        "Subtotal": [r'subtotal', r'net', r'amount'],
        "Tax": [r'tax', r'vat', r'gst'],
        "Total": [r'total', r'balance', r'amount due']
    }

    for line in lines:
        for field, patterns in field_patterns.items():
            if not structured_data[field]:
                for pattern in patterns:
                    match = re.search(f"{pattern}[: ]+(\d+\.\d{2})", line, re.IGNORECASE)
                    if match:
                        structured_data[field] = float(match.group(1))
                        break

    return structured_data

# Streamlit app
st.title("Receipt Processor")

# File upload
uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Load image using PIL
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    # Preprocess and process receipt
    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)
    receipt_data = parse_receipt_text(extracted_text)

    # Display extracted data
    st.subheader("Extracted Receipt Data")
    for key, value in receipt_data.items():
        if key == "Items":
            st.write(f"{key}:")
            for item in value:
                st.write(f"  - {item['Item']}: {item['Price']}")
        else:
            st.write(f"{key}: {value}")
else:
    st.write("Please upload a receipt image.")
