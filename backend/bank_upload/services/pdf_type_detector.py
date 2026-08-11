"""
pdf_type_detector.py — Bank Statement PDF Classification Service
===============================================================
Determines whether an uploaded PDF file contains a usable native digital text layer
or requires vision/OCR processing.

Classification Criteria:
  - Page count
  - Character count per page
  - Percentage of pages containing readable text (>100 characters)
  - Text density
"""
import logging
import pypdf

logger = logging.getLogger('bank_upload.pdf_type_detector')


def detect_pdf_type(file_bytes: bytes) -> dict:
    """
    Inspects PDF structure and returns classification metadata dictionary:
      {
          "pdf_type": "digital" | "scanned",
          "text_layer_present": bool,
          "confidence": float,
          "pages": int,
          "char_count_total": int,
          "avg_chars_per_page": float
      }
    """
    try:
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        if total_pages == 0:
            return {
                "pdf_type": "scanned",
                "text_layer_present": False,
                "confidence": 0.0,
                "pages": 0,
                "char_count_total": 0,
                "avg_chars_per_page": 0.0
            }

        total_chars = 0
        usable_pages = 0

        for page in reader.pages:
            t = page.extract_text() or ""
            chars = len(t.strip())
            total_chars += chars
            if chars > 100:
                usable_pages += 1

        pct_usable = usable_pages / total_pages if total_pages > 0 else 0.0
        is_digital = pct_usable >= 0.8 and (total_chars / total_pages) > 200

        result = {
            "pdf_type": "digital" if is_digital else "scanned",
            "text_layer_present": is_digital,
            "confidence": round(pct_usable, 2),
            "pages": total_pages,
            "char_count_total": total_chars,
            "avg_chars_per_page": round(total_chars / total_pages, 1)
        }
        logger.info(
            f"📄 [PDF TYPE DETECTOR] Result: pdf_type='{result['pdf_type']}' "
            f"| confidence={result['confidence']} | pages={total_pages} | total_chars={total_chars}"
        )
        return result
    except Exception as e:
        logger.warning(f"⚠️ [PDF TYPE DETECTOR] Error inspecting PDF bytes: {e}. Defaulting to 'scanned'.")
        return {
            "pdf_type": "scanned",
            "text_layer_present": False,
            "confidence": 0.0,
            "pages": 0,
            "char_count_total": 0,
            "avg_chars_per_page": 0.0
        }
