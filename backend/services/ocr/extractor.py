import os
import re
import pdfplumber
from PIL import Image
import pytesseract

class OCRUnreadableError(Exception):
    pass

def _is_meaningful_text(text: str) -> bool:
    if not text:
        return False
    valid_chars = re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]", text)
    return len(valid_chars) >= 3

def extract_text_from_file(uploaded_file) -> str:
    filename = getattr(uploaded_file, "name", "").lower()
    ext = os.path.splitext(filename)[1]
    extracted_text = ""

    try:
        uploaded_file.seek(0)
        if ext == ".pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                pdf_texts = [page.extract_text() for page in pdf.pages if page.extract_text()]
                extracted_text = "\n".join(pdf_texts)
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            image = Image.open(uploaded_file)
            extracted_text = pytesseract.image_to_string(image, lang="jpn+eng")
        uploaded_file.seek(0)
    except Exception as exc:
        raise OCRUnreadableError("The uploaded document could not be read clearly.") from exc

    cleaned_text = extracted_text.strip()
    if not _is_meaningful_text(cleaned_text):
        raise OCRUnreadableError("The uploaded document could not be read clearly.")

    return cleaned_text
