import base64
import numpy as np
import easyocr
from PIL import Image
import io

reader = easyocr.Reader(['en'])

def extract_text_from_base64(base64_str: str) -> str:
    try:
        if not base64_str:
            return ""

        # remove data URL prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        img_data = base64.b64decode(base64_str)

        # convert to PIL image
        image = Image.open(io.BytesIO(img_data)).convert("RGB")

        # convert to numpy (what EasyOCR needs)
        img_array = np.array(image)

        results = reader.readtext(img_array)

        if not results:
            return "OCR_EMPTY: no text found"

        text = " ".join([word for _, word, conf in results if conf > 0.3])

        return text.strip() if text.strip() else "OCR_EMPTY"

    except Exception as e:
        return f"OCR_ERROR: {str(e)}"