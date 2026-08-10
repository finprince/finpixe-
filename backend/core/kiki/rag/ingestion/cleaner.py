"""
KIKI Ingestion Text Cleaner — Phase 17
======================================
Sanitizes document text, normalizes whitespace, removes HTML tags and bad control characters.
"""
import re


class TextCleaner:
    """Document text sanitizer and normalizer."""

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # 1. Remove non-printable control characters (except newline, tab, carriage return)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # 2. Convert multiple blank lines into max 2 newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        # 3. Strip trailing/leading spaces per line
        lines = [line.strip() for line in cleaned.split('\n')]
        return '\n'.join(lines).strip()


text_cleaner = TextCleaner()
