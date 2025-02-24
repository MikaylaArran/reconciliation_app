import openpyxl
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageEnhance
import pytesseract
import re
import io
import cv2
import numpy as np
import streamlit as st

# ------------------------
# CONFIGURATION
# ------------------------
# Configure Tesseract OCR path (update if necessary)
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"  # Update for Windows or Mac if needed

# ------------------------
# IMAGE PROCESSING
# ------------------------
def preprocess_image(image):
    """Preprocess the image to improve OCR results, especially for blurry slips."""
    # Convert PIL image to OpenCV format
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    image_cv = cv2.resize(image_cv, (1024, 1024), interpolation=cv2.INTER_AREA)  # Resize to optimize performance
    
    # Convert to grayscale
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    
    # Sharpen image using kernel
    kernel = np.array([[0, -1, 0], 
                       [-1, 5,-1], 
                       [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    
    # Apply Gaussian Blur to reduce noise
    blurred = cv2.GaussianBlur(sharpened, (3, 3), 0)
    
    # Thresholding
    _, binary = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to PIL format
    processed_image = Image.fromarray(binary)
    return processed_image

def extract_text(image):
    """Extract text from the image using Tesseract."""
    # Use a more flexible OCR config for blurry text
    ocr_config = r'--oem 3 --psm 4'  # PSM 4 works better for text blocks with blurry or skewed text
    return pytesseract.image_to_string(image, config=ocr_config)

def extract_data_with_boxes(image):
    """Extract text and bounding box data from the image."""
    ocr_config = r'--oem 3 --psm 4'
    data = pytesseract.image_to_data(image, config=ocr_config, output_type=pytesseract.Output.DICT)
    boxes = []
    for i in range(len(data['level'])):
        try:
            conf = float(data['conf'][i])
        except:
            conf = 0
        if conf > 45 and data['text'][i].strip():
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
    """Draw bounding boxes around detected text for visualization."""
    draw = ImageDraw.Draw(image)
    for box in boxes:
        left, top = box['left'], box['top']
        right, bottom = left + box['width'], top + box['height']
        draw.rectangle([left, top, right, bottom], outline="red", width=2)
    return image

# ------------------------
# TEXT EXTRACTION
# ------------------------
def extract_dates(text):
    """Extract dates from text in multiple formats."""
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',   
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{2,4}\b',
        r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b'
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(set(dates))

def extract_amounts(text):
    """Extract currency amounts in various formats."""
    amount_patterns = [
        r'([€£$R])\s?(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2})?)',
        r'(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2})?)\s?(USD|EUR|GBP|ZAR)'
    ]
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                symbol = match[0] if re.match(r'[$€£R]', match[0]) else match[1]
                num_str = match[1] if re.match(r'[$€£R]', match[0]) else match[0]
                try:
                    amount_value = float(num_str.replace(" ", "").replace(",", ""))
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
    """Extract company name from the first few lines."""
    lines = text.split("\n")
    for line in lines[:5]:
        cline = line.strip()
        if cline and len(cline) > 3 and re.search(r'[A-Za-z]', cline):
            if sum(1 for c in cline if c.isupper()) >= len(cline) * 0.3:
                return cline
    return next((line.strip() for line in lines if line.strip()), None)

def extract_items(text):
    """Extract item names and prices from the text."""
    lines = text.split("\n")
    items = []
    item_pattern = r'^(.*?)[\s\-:]+([\d,]+\.\d{2})$'
    for line in lines:
        match = re.match(item_pattern, line)
        if match:
            item_name = match.group(1).strip()
            try:
                price = float(match.group(2).replace(",", ""))
                items.append({"Item": item_name, "Price": price})
            except:
                pass
    return items

def find_value_near_keywords(lines, keywords, value_pattern=r"(\d{1,3}(?:[,\.\s]\d{3})*(?:[,\.\s]\d{2}))"):
    """Find values near specific keywords like Subtotal, Tax, and Total."""
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
    """Parse the OCR text into structured receipt data."""
    structured_data = {
        "Company Name": extract_company_name(text),
        "Dates": extract_dates(text),
        "Amounts": extract_amounts(text),
        "Items": extract_items(text)
    }
    lines = text.split("\n")
    synonyms = {
        "Subtotal": [r'subtotal', r'sub-total', r'net amount', r'amount before vat', r'exclusive amount', r'excl\. vat'],
        "Tax (VAT)": [r'vat', r'vat amount', r'value-added tax', r'tax \(vat\)', r'vat @ \d+%', r'incl\. vat', r'excl\. vat', r'vat payable'],
        "Total": [r'total', r'grand total', r'total payable', r'final amount', r'inclusive total', r'amount due', r'balance due']
    }
    for field, keywords in synonyms.items():
        structured_data[field] = find_value_near_keywords(lines, keywords)
    return structured_data

# ------------------------
# EXCEL EXPORT
# ------------------------
def create_excel(receipt_data):
    """Generate an Excel file from the parsed receipt data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Receipt Data"
    ws.append(["Field", "Value"])
    ws.append(["Company Name", receipt_data.get("Company Name")])
    ws.append(["Dates", ", ".join(receipt_data.get("Dates", []))])
    for field in ["Subtotal", "Tax (VAT)", "Total"]:
        ws.append([field, receipt_data.get(field)])
    amounts = receipt_data.get("Amounts", [])
    ws.append(["Amounts", ", ".join([f"{sym}{amt:.2f}" for sym, amt in amounts]) if amounts else ""])
    ws.append([])
    ws.append(["Items", "Price"])
    for item in receipt_data.get("Items", []):
        ws.append([item["Item"], item["Price"]])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# ------------------------
# STREAMLIT APP INTERFACE
# ------------------------
st.title("Receipt Processor with Enhanced Blurry Slip Detection")

uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)  
    
    processed_image = preprocess_image(image)
    extracted_text = extract_text(processed_image)
    boxes = extract_data_with_boxes(processed_image)
    
    st.subheader("Raw OCR Text")
    st.text(extracted_text)
    
    if st.button("Show Image with Bounding Boxes"):
        image_with_boxes = draw_boxes_on_image(processed_image.copy(), boxes)
        st.image(image_with_boxes, caption="Image with Bounding Boxes", use_container_width=True)  
    
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
