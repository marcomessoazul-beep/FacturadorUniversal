import re
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s<>()]+|(?:www\.)[^\s<>()]+\.[a-zA-Z]{2,}[^\s<>()]*", re.I)

def read_qr(image_path):
    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is None:
            return ""
        detector = cv2.QRCodeDetector()
        value, points, _ = detector.detectAndDecode(img)
        return (value or "").strip()
    except Exception:
        return ""

def read_ocr(image_path, tesseract_cmd=""):
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageFilter
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        img = Image.open(image_path).convert("RGB")
        gray = ImageOps.grayscale(img)
        gray = gray.resize((gray.width * 2, gray.height * 2))
        gray = gray.filter(ImageFilter.SHARPEN)
        return pytesseract.image_to_string(gray, lang="spa+eng")
    except Exception as e:
        return f"[OCR_ERROR] {e}"

def find_urls(text):
    urls = []
    for match in URL_RE.findall(text or ""):
        url = match.rstrip(".,;:)")
        if url.startswith("www."):
            url = "https://" + url
        if url not in urls:
            urls.append(url)
    return urls

def detect_merchant(text):
    t = (text or "").upper()
    merchants = [
        ("Walmart", ["WALMART"]),
        ("Sam's Club", ["SAM'S", "SAMS CLUB", "SAMSCLUB"]),
        ("Costco", ["COSTCO"]),
        ("Farmacias del Ahorro", ["FARMACIAS DEL AHORRO", "FARMACIA DEL AHORRO"]),
        ("Abarrotes El Zorro", ["ABARROTES EL ZORRO", "EL ZORRO"]),
        ("Soriana", ["SORIANA"]),
        ("HEB", [" HEB ", "H-E-B"]),
        ("Chedraui", ["CHEDRAUI"]),
    ]
    for name, needles in merchants:
        if any(n in f" {t} " for n in needles):
            return name
    return "Comercio no identificado"

def extract_data(text):
    t = " ".join((text or "").split())
    data = {}

    patterns = {
        "rfc": [r"\bRFC[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})\b"],
        "cp": [r"(?:C\.?P\.?|CÓDIGO POSTAL)[:\s]*(\d{5})"],
        "ticket": [r"(?:TICKET|FOLIO|NO\.?\s*TICKET|N[ÚU]M(?:ERO)?\s*DE\s*TICKET)[:#\s-]*([A-Z0-9-]{4,})"],
        "tc": [r"\bTC[:#\s-]*([0-9]{6,30})\b"],
        "tr": [r"\bTR[:#\s-]*([0-9]{3,15})\b"],
        "itu": [r"\bITU[:#\s-]*([A-Z0-9-]{4,30})\b"],
        "total": [r"(?:TOTAL|IMPORTE|A PAGAR)[:\s]*\$?\s*([0-9][0-9,]*\.[0-9]{2})"],
        "fecha": [r"(?:FECHA|DATE)[:\s]*([0-3]?\d[/-][01]?\d[/-][12]\d{3,4})"],
        "hora": [r"(?:HORA|TIME)[:\s]*([0-2]?\d[:.][0-5]\d)"],
    }
    for key, pats in patterns.items():
        for p in pats:
            m = re.search(p, t, re.I)
            if m:
                data[key] = m.group(1)
                break
    return data

def analyze_ticket(image_path, tesseract_cmd=""):
    qr = read_qr(image_path)
    ocr = read_ocr(image_path, tesseract_cmd)
    combined = "\n".join(x for x in [qr, ocr] if x)
    urls = find_urls(combined)
    merchant = detect_merchant(combined)
    data = extract_data(combined)
    return {
        "merchant": merchant,
        "qr_url": qr if qr.startswith(("http://", "https://", "www.")) else "",
        "urls": urls,
        "raw_text": combined,
        "data": data
    }
