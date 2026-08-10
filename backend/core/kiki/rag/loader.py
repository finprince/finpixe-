"""
KIKI Document Loader Module
============================
Parses and normalizes unstructured documents (PDF, DOCX, TXT, Markdown, CSV, HTML).
"""
import os
import re
from typing import Dict, Any, List

class DocumentLoader:
    """Enterprise Document Loader for unstructured knowledge ingestion."""

    SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".html", ".htm"]

    def load_document(self, file_path: str, filename: str = None) -> Dict[str, Any]:
        """
        Loads document content and extracts raw text, page count, and structural metadata.
        """
        filename = filename or os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: {self.SUPPORTED_EXTENSIONS}")

        content_pages = []
        full_text = ""
        page_metadata_available = False  # Phase 17.4: default; set True only for real PDF pages

        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            full_text = raw_text
            # TXT/MD has no physical page structure — flag as unavailable
            content_pages.append({"page": 1, "text": raw_text, "page_metadata_available": False})
            page_metadata_available = False

        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for idx, page in enumerate(reader.pages):
                    p_text = page.extract_text() or ""
                    # PDF pages from pypdf are real physical pages
                    content_pages.append({"page": idx + 1, "text": p_text, "page_metadata_available": True})
                    full_text += f"\n--- Page {idx + 1} ---\n" + p_text
                page_metadata_available = True
            except ImportError:
                # Fallback: no real page extraction — treat as single blob
                with open(file_path, "rb") as f:
                    raw_bytes = f.read()
                clean_text = re.sub(b'[^\x20-\x7E\n\r\t]', b' ', raw_bytes).decode('utf-8', errors='ignore')
                full_text = clean_text
                content_pages.append({"page": 1, "text": clean_text, "page_metadata_available": False})
                page_metadata_available = False

        elif ext in [".docx", ".doc"]:
            # Phase 17.4: DOCX provides no physical page boundaries via python-docx.
            # page_metadata_available = False so citations never print "Page 1".
            try:
                import docx
                doc = docx.Document(file_path)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                full_text = "\n".join(paras)
                content_pages.append({"page": 1, "text": full_text, "page_metadata_available": False})
            except Exception:
                with open(file_path, "rb") as f:
                    raw_bytes = f.read()
                clean_text = re.sub(b'[^\x20-\x7E\n\r\t]', b' ', raw_bytes).decode('utf-8', errors='ignore')
                full_text = clean_text
                content_pages.append({"page": 1, "text": clean_text, "page_metadata_available": False})
            page_metadata_available = False

        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            full_text = raw_text
            content_pages.append({"page": 1, "text": raw_text, "page_metadata_available": False})
            page_metadata_available = False

        elif ext in [".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_html = f.read()
            clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
            full_text = clean_text
            content_pages.append({"page": 1, "text": clean_text, "page_metadata_available": False})
            page_metadata_available = False

        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            full_text = raw_text
            content_pages.append({"page": 1, "text": raw_text, "page_metadata_available": False})
            page_metadata_available = False

        return {
            "filename": filename,
            "extension": ext,
            "full_text": full_text.strip(),
            "pages": content_pages,
            "total_pages": len(content_pages),
            # Phase 17.4: True only when pages carry real physical page numbers (PDF).
            # DOCX/TXT/MD/CSV/HTML always False — do not cite Page N for these.
            "page_metadata_available": page_metadata_available,
        }

document_loader = DocumentLoader()
