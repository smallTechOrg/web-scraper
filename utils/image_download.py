# utils/image_download.py

import os
import requests
import tempfile
from urllib.parse import urlparse

def get_image_file(image_ref):
    """
    Accepts either a local path or an HTTPS URL (signed URLs like GCS format).
    Downloads the image to a temp file if URL, preserves extension if possible.
    Returns a local file path ready for Playwright upload.
    Works on Windows and Linux.
    """
    parsed = urlparse(image_ref)

    # If HTTPS URL (always the case for your URLs)
    if parsed.scheme == "https":
        # Get extension from URL path
        ext = os.path.splitext(os.path.basename(parsed.path))[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png"]:
            ext = ".jpg"  # fallback

        temp_path = os.path.join(tempfile.gettempdir(), f"upload_image{ext}")

        print(f"Downloading image from URL: {image_ref}")
        response = requests.get(image_ref, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Saved image to {temp_path}")
            return temp_path
        else:
            raise Exception(f"Failed to download image: {image_ref}, status: {response.status_code}")

    # Otherwise, treat as local file path
    if os.path.exists(image_ref):
        print(f"Using local image file: {image_ref}")
        return image_ref
    else:
        raise FileNotFoundError(f"Image file not found: {image_ref}")