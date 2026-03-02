# portals/services/captcha_solver.py

import easyocr
import cv2

_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        # CPU only
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader

def solve_captcha(image_path: str) -> str:
    """
    Reads captcha text from an image using EasyOCR (CPU).
    """
    img = cv2.imread(image_path)
    if img is None:
        return ""

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale for better OCR
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Simple thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    reader = _get_reader()
    results = reader.readtext(thresh, detail=0)

    if not results:
        return ""

    # Join all detected text and clean it
    captcha_text = ''.join(results).strip()
    
    # Remove any special characters that might interfere, keep only alphanumeric
    cleaned_text = ''.join(c for c in captcha_text if c.isalnum())
    
    return cleaned_text if cleaned_text else captcha_text