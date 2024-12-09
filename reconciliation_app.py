import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import re

# Configure Tesseract OCR path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"

# Preprocess image for OCR
def preprocess_image(image):
    # Convert to grayscale
    grayscale_image = ImageOps.grayscale(image)

    # Enhance edges to improve text clarity
    enhanced_image = grayscale_image.filter(ImageFilter.EDGE_ENHANCE)

    # Apply binary thresholding to make text stand out
    binary_image = enhanced_image.point(lambda x: 0 if x < 150 else 255)
    
    return binary_image

# Extract text from the preprocessed image
def extract_text(image):
    ocr_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(image, config=ocr_config)

# Find field value near keywords
def find_value_near_keywords(lines, keywords, value_pattern=r"(\d{1,3}(?:,\d{3})*\.\d{2})"):
    for i, line in enumerate(lines):
        for keyword in keywords:
            if re.search(keyword, line, re.IGNORECASE):
                # Search for value in the same line
                value_match = re.search(value_pattern, line)
                if value_match:
                    return float(value_match.group(1).replace(",", ""))
                # If no value in the same line, check the next line
                elif i + 1 < len(lines):
                    next_line_match = re.search(value_pattern, lines[i + 1])
                    if next_line_match:
                        return float(next_line_match.group(1).replace(",", ""))
    return None

# Parse receipt text into structured fields
def parse_receipt_text(text):
    lines = text.split("\n")
    structured_data = {
        "Company Name": None,
        "Date": None,
        "Items": [],
        "Subtotal": None,
        "Tax (VAT)": None,
        "Total": None
    }

    # Extract company name (assume it's in the first few lines)
    for line in lines[:3]:
        if line.strip():
            structured_data["Company Name"] = line.strip()
            break

    # Extract date using regex
    date_pattern = r'\d{1,2} [A-Za-z]{3,} \d{4}'  # Handles formats like "12 Dec 2023"
    for line in lines:
        date_match = re.search(date_pattern, line)
        if date_match:
            structured_data["Date"] = date_match.group()
            break

    # Extract items and their prices
    item_pattern = r'(.*)\s+R?\s?(\d{1,3}(?:,\d{3})*\.\d{2})$'
    for line in lines:
        item_match = re.match(item_pattern, line)
        if item_match:
            item_name = item_match.group(1).strip()
            item_price = float(item_match.group(2).replace(",", ""))
            structured_data["Items"].append({"Item": item_name, "Price": item_price})

    # Synonyms for Subtotal, Tax (VAT), and Total
    synonyms = {
        "Subtotal": [
            r'subtotal', r'sub-total', r'net amount', r'amount before vat',
            r'exclusive amount', r'excl\. vat'
        ],
        "Tax (VAT)": [
            r'vat', r'vat amount', r'value-added tax', r'tax \(vat\)',
            r'vat @ \d+%', r'incl\. vat', r'excl\. vat', r'vat payable'
        ],
        "Total": [
            r'total', r'grand total', r'total payable', r'final amount',
            r'inclusive total', r'amount due', r'balance due'
        ]
    }

    # Extract Subtotal, Tax (VAT), and Total
    for field, keywords in synonyms.items():
        structured_data[field] = find_value_near_keywords(lines, keywords)

    return structured_data

# Streamlit App Interface
st.title("Refined Receipt Processor")

# Dropdown for Account Selection
accounts = [
    "Sales Revenue", "Office Supplies", "Travel Expenses", 
    "Miscellaneous Expenses", "Tax Payments"
]
selected_account = st.selectbox("Select an Account Category", accounts)
st.write(f"Selected Account: {selected_account}")

# Upload file
uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Load the image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    # Preprocess and process the image
    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)
    st.text(f"Raw OCR Text:\n{extracted_text}")  # Debugging: Display raw OCR text
    receipt_data = parse_receipt_text(extracted_text)

    # Display the structured data
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
