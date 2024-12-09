import cv2
import pytesseract
import re
from PIL import Image, ImageOps

# Configure Tesseract executable path
pytesseract.pytesseract_cmd = "/usr/bin/tesseract"

# Preprocessing: Deskew, denoise, enhance
def preprocess_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Remove noise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # Deskew the image
    coords = cv2.findNonZero(cv2.bitwise_not(denoised))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = denoised.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Thresholding for better OCR
    _, binary = cv2.threshold(deskewed, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

# Extract text using OCR
def extract_text(image):
    ocr_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(image, config=ocr_config)

# Parse receipt text into structured data
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

# Main function
def process_receipt(image_path):
    # Preprocess image for better OCR accuracy
    processed_image = preprocess_image(image_path)
    
    # Convert processed image to PIL format for OCR
    pil_image = Image.fromarray(processed_image)
    
    # Extract and parse text
    extracted_text = extract_text(pil_image)
    structured_data = parse_receipt_text(extracted_text)
    return structured_data

# Run the process on a sample receipt
image_path = '/mnt/data/images-2.jpeg'  # Replace with your file path
receipt_data = process_receipt(image_path)

# Display results
print("Structured Receipt Data:")
for key, value in receipt_data.items():
    if key == "Items":
        print(f"{key}:")
        for item in value:
            print(f"  - {item['Item']}: {item['Price']}")
    else:
        print(f"{key}: {value}")
