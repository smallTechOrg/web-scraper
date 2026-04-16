import easyocr
import multiprocessing
import os
import cv2


def _ocr_worker(image_path, queue):
    """
    Runs inside a separate process to prevent main app crash (OOM safe)
    """
    try:
        # 🔥 Reduce CPU + memory usage BEFORE importing easyocr
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["MKL_NUM_THREADS"] = "1"

        import easyocr

        # Load reader inside worker (important)
        reader = easyocr.Reader(
            ['en'],
            gpu=False,
            verbose=False,
            quantize=True   # 🔥 reduces memory significantly
        )

        img = cv2.imread(image_path)
        if img is None:
            queue.put("")
            return

        # ===== Your preprocessing (kept) =====
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        gray = cv2.resize(
            gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )

        _, thresh = cv2.threshold(
            gray, 150, 255, cv2.THRESH_BINARY
        )

        results = reader.readtext(thresh, detail=0)

        if not results:
            queue.put("")
            return

        captcha_text = ''.join(results).strip()
        cleaned_text = ''.join(c for c in captcha_text if c.isalnum())

        queue.put(cleaned_text if cleaned_text else captcha_text)

    except Exception as e:
        print("🔥 OCR worker error:", str(e))
        queue.put("")


def solve_captcha(image_path: str, timeout=30) -> str:
    """
    Safe OCR wrapper (prevents Flask crash if memory spikes)
    """
    queue = multiprocessing.Queue()

    process = multiprocessing.Process(
        target=_ocr_worker,
        args=(image_path, queue)
    )

    process.start()
    process.join(timeout)

    # 🔥 Kill if stuck or too heavy
    if process.is_alive():
        process.terminate()
        process.join()
        print("⚠️ OCR killed (timeout/memory)")
        return ""

    if not queue.empty():
        return queue.get()

    return ""