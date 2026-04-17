import os
import cv2
import easyocr

# 🔥 Reduce CPU threads (helps memory too)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# ✅ Load EasyOCR ONCE (global)
print("🔄 Loading EasyOCR model (one-time)...")
reader = easyocr.Reader(
    ['en'],
    gpu=False,
    verbose=False,
    quantize=True,
)
print("✅ EasyOCR loaded")


def solve_captcha(image_path: str) -> str:
    """
    Optimized OCR (low memory, no multiprocessing)
    """

    try:
        img = cv2.imread(image_path)
        if img is None:
            return ""

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ⚠️ Reduce scaling (was 2x → now 1.2x)
        gray = cv2.resize(
            gray,
            None,
            fx=1.2,
            fy=1.2,
            interpolation=cv2.INTER_LINEAR
        )

        # Threshold
        _, thresh = cv2.threshold(
            gray,
            150,
            255,
            cv2.THRESH_BINARY
        )

        # OCR
        results = reader.readtext(thresh, detail=0)

        if not results:
            return ""

        captcha_text = ''.join(results).strip()

        # Clean non-alphanumeric
        cleaned_text = ''.join(c for c in captcha_text if c.isalnum())

        # 🔥 Explicit cleanup (important on small RAM)
        del img
        del gray
        del thresh

        return cleaned_text if cleaned_text else captcha_text

    except Exception as e:
        print("🔥 OCR error:", str(e))
        return ""