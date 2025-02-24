import openpyxl
from PIL import Image, ImageOps, ImageFilter, ImageDraw
import pytesseract
import re
import io
import streamlit as st

# Configure Tesseract OCR path (update if necessary)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# ------------------------
# Image Preprocessing
# ------------------------
def preprocess_image(image):
    grayscale_image = ImageOps.grayscale(image)
    enhanced_image = ImageOps.autocontrast(grayscale_image)
    denoised_image = enhanced_image.filter(ImageFilter.MedianFilter(size=3))
    binary_image = denoised_image.point(lambda x: 0 if x < 150 else 255)
    return binary_image

# ------------------------
# OCR Extraction
# ------------------------
def extract_text(image):
    ocr_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(image, config=ocr_config)

def extract_data_with_boxes(image):
    ocr_config = r'--oem 3 --psm 6'
    data = pytesseract.image_to_data(image, config=ocr_config, output_type=pytesseract.Output.DICT)
    n_boxes = len(data['level'])
    boxes = []
    for i in range(n_boxes):
        try:
            conf = float(data['conf'][i])
        except:
            conf = 0
        if conf > 50 and data['text'][i].strip():
            boxes.append({
                'text': data['text'][i],
                'left': data['left'][i],
                'top': data['top'][i],
                'width': data['width'][i],
                'height': data['height'][i],
                'conf': conf
            })
    return boxes

def draw_boxes_on_image(image, boxes):
    draw = ImageDraw.Draw(image)
    for box in boxes:
        left = box['left']
        top = box['top']
        right = left + box['width']
        bottom = top + box['height']
        draw.rectangle([left, top, right, bottom], outline="red", width=2)
    return image

# ------------------------
# Advanced Field Extraction
# ------------------------
def extract_dates(text):
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # 12/31/2020 or 31-12-2020
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',      # 2020-12-31
        r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}\b',  # 31 Jan 2020
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{2,4}\b',  # Jan 31, 2020
        r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b'         # 31.12.2020
    ]
    dates = []
    for pattern in date_patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            dates.extend(found)
    return list(set(dates))

def extract_amounts(text):
    amount_patterns = [
        r'([€£$R])\s?(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2})?)',
        r'(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2})?)\s?(USD|EUR|GBP|ZAR)'
    ]
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                if re.match(r'[$€£R]', match[0]):
                    symbol = match[0]
                    num_str = match[1]
                else:
                    symbol = match[1]
                    num_str = match[0]
                num_clean = num_str.replace(" ", "").replace(",", "")
                try:
                    amount_value = float(num_clean)
                    amounts.append((symbol, amount_value))
                except:
                    pass
            else:
                try:
                    amt = float(match.replace(" ", "").replace(",", ""))
                    amounts.append(("", amt))
                except:
                    pass
    return amounts

def extract_company_name(text):
    lines = text.split("\n")
    for line in lines[:5]:
        cline = line.strip()
        if cline and len(cline) > 3 and re.search(r'[A-Za-z]', cline):
            if sum(1 for c in cline if c.isupper()) >= len(cline) * 0.3:
                return cline
    for line in lines:
        if line.strip():
            return line.strip()
    return None

def extract_items(text):
    lines = text.split("\n")
    items = []
    item_pattern = r'^(.*?)[\s\-:]+([\d,]+\.\d{2})$'
    for line in lines:
        match = re.match(item_pattern, line)
        if match:
            item_name = match.group(1).strip()
            try:
                price = float(match.group(2).replace(",", ""))
            except:
                price = None
            items.append({"Item": item_name, "Price": price})
    return items

def find_value_near_keywords(lines, keywords, value_pattern=r"(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2}))"):
    for i, line in enumerate(lines):
        for keyword in keywords:
            if re.search(keyword, line, re.IGNORECASE):
                value_match = re.search(value_pattern, line)
                if value_match:
                    try:
                        return float(value_match.group(1).replace(" ", "").replace(",", ""))
                    except:
                        pass
                elif i + 1 < len(lines):
                    next_line_match = re.search(value_pattern, lines[i + 1])
                    if next_line_match:
                        try:
                            return float(next_line_match.group(1).replace(" ", "").replace(",", ""))
                        except:
                            pass
    return None

def parse_receipt_text_enhanced(text):
    structured_data = {}
    structured_data["Company Name"] = extract_company_name(text)
    structured_data["Dates"] = extract_dates(text)
    structured_data["Amounts"] = extract_amounts(text)
    structured_data["Items"] = extract_items(text)
    lines = text.split("\n")
    synonyms = {
        "Subtotal": [r'subtotal', r'sub-total', r'net amount', r'amount before vat', r'exclusive amount', r'excl\. vat'],
        "Tax (VAT)": [r'vat', r'vat amount', r'value-added tax', r'tax \(vat\)', r'vat @ \d+%', r'incl\. vat', r'excl\. vat', r'vat payable'],
        "Total": [r'total', r'grand total', r'total payable', r'final amount', r'inclusive total', r'amount due', r'balance due']
    }
    for field, keywords in synonyms.items():
        structured_data[field] = find_value_near_keywords(lines, keywords)
    return structured_data

def create_excel(receipt_data):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Receipt Data"
    ws.append(["Field", "Value"])
    for key in ["Company Name"]:
        ws.append([key, receipt_data.get(key)])
    ws.append(["Dates", ", ".join(receipt_data.get("Dates", []))])
    for field in ["Subtotal", "Tax (VAT)", "Total"]:
        ws.append([field, receipt_data.get(field)])
    amounts = receipt_data.get("Amounts", [])
    if amounts:
        amounts_str = ", ".join([f"{sym}{amt:.2f}" for sym, amt in amounts])
    else:
        amounts_str = ""
    ws.append(["Amounts", amounts_str])
    ws.append([])
    ws.append(["Items", "Price"])
    for item in receipt_data.get("Items", []):
        ws.append([item["Item"], item["Price"]])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# ------------------------
# Streamlit App Interface
# ------------------------
st.title("Receipt Processor")

uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)
    
    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)
    boxes = extract_data_with_boxes(processed_image)
    
    st.subheader("Raw OCR Text")
    st.text(extracted_text)
    
    if st.button("Show Image with Bounding Boxes"):
        image_with_boxes = draw_boxes_on_image(processed_image.copy(), boxes)
        st.image(image_with_boxes, caption="Image with Bounding Boxes", use_column_width=True)
    
    receipt_data = parse_receipt_text_enhanced(extracted_text)
    
    st.subheader("Extracted Receipt Data")
    st.write("**Company Name:**", receipt_data.get("Company Name"))
    st.write("**Dates Found:**", receipt_data.get("Dates"))
    st.write("**Subtotal:**", receipt_data.get("Subtotal"))
    st.write("**Tax (VAT):**", receipt_data.get("Tax (VAT)"))
    st.write("**Total:**", receipt_data.get("Total"))
    st.write("**Amounts (if any):**", receipt_data.get("Amounts"))
    st.write("**Items:**")
    for item in receipt_data.get("Items", []):
        st.write(f"- {item['Item']}: {item['Price']}")
    
    excel_buffer = create_excel(receipt_data)
    st.download_button(
        label="Download Excel File",
        data=excel_buffer,
        file_name="receipt_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.write("Please upload a receipt image.")
