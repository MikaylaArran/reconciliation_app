import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import re
from difflib import get_close_matches

pytesseract.pytesseract_cmd = "/usr/bin/tesseract"

def preprocess_image(image):
    grayscale_image = ImageOps.grayscale(image)
    enhanced_image = ImageOps.autocontrast(grayscale_image)
    denoised_image = enhanced_image.filter(ImageFilter.MedianFilter(size=3))
    binary_image = denoised_image.point(lambda x: 0 if x < 150 else 255)
    return binary_image

def extract_text(image):
    ocr_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(image, config=ocr_config)

def find_closest_keyword(line, keywords):
    matches = get_close_matches(line.lower(), keywords, n=1, cutoff=0.5)
    return matches[0] if matches else None

def find_value_near_keywords(lines, keywords, value_pattern=r"(\d{1,3}(?:,\d{3})*\.\d{2})"):
    keywords_lower = [k.lower() for k in keywords]
    for i, line in enumerate(lines):
        matched_keyword = find_closest_keyword(line, keywords_lower)
        if matched_keyword:
            value_match = re.search(value_pattern, line)
            if value_match:
                return float(value_match.group(1).replace(",", ""))
            elif i + 1 < len(lines):
                next_line_match = re.search(value_pattern, lines[i + 1])
                if next_line_match:
                    return float(next_line_match.group(1).replace(",", ""))
    return None

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

    for line in lines[:3]:
        if line.strip():
            structured_data["Company Name"] = line.strip()
            break

    date_pattern = r'\d{1,2} [A-Za-z]{3,} \d{4}'
    for line in lines:
        date_match = re.search(date_pattern, line)
        if date_match:
            structured_data["Date"] = date_match.group()
            break

    item_pattern = r'(.*)\s+R?\s?(\d{1,3}(?:,\d{3})*\.\d{2})$'
    for line in lines:
        item_match = re.match(item_pattern, line)
        if item_match:
            item_name = item_match.group(1).strip()
            item_price = float(item_match.group(2).replace(",", ""))
            structured_data["Items"].append({"Item": item_name, "Price": item_price})

    synonyms = {
        "Subtotal": [
            r'subtotal', r'sub-total', r'net amount', r'amount before vat',
            r'exclusive amount', r'excl\. vat'
        ],
        "Tax (VAT)": [
            r'vat', r'vat amount', r'value-added tax', r'tax \(vat\)',
            r'vat @ \d+%', r'incl\. vat', r'excl\. vat', r'vat payable', r'rate.*vat'
        ],
        "Total": [
            r'total', r'grand total', r'total payable', r'final amount',
            r'inclusive total', r'amount due', r'balance due'
        ]
    }

    for field, keywords in synonyms.items():
        structured_data[field] = find_value_near_keywords(lines, keywords)

    return structured_data

st.title("Enhanced Receipt Processor with Debugging")

uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)
    st.text(f"Raw OCR Text:\n{extracted_text}")

    receipt_data = parse_receipt_text(extracted_text)

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
