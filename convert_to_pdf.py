import markdown
import os
from xhtml2pdf import pisa

md_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.md"
html_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.html"
pdf_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.pdf"

# Read Markdown
with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Convert Markdown to HTML with extensions
html = markdown.markdown(text, extensions=['tables', 'fenced_code'])

# Add CSS that works well with xhtml2pdf
css = """
<style>
    @page {
        size: a4 portrait;
        margin: 2cm;
    }
    body {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 12pt;
        color: #333333;
    }
    h1 { color: #2c3e50; border-bottom: 1px solid #3498db; padding-bottom: 5px; }
    h2 { color: #2980b9; margin-top: 20px; }
    h3 { color: #16a085; }
    table {
        width: 100%;
        border: 1px solid #000;
    }
    th { background-color: #34495e; color: #ffffff; padding: 8px; font-weight: bold; border: 1px solid #000;}
    td { padding: 8px; border: 1px solid #000; }
    img { zoom: 50%; }
    blockquote {
        color: #c0392b;
        font-weight: bold;
    }
</style>
"""

full_html = f"<html><head>{css}</head><body>{html}</body></html>"

# Write HTML (just in case)
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

# Generate PDF
with open(pdf_path, "wb") as result_file:
    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(full_html, dest=result_file)

if pisa_status.err:
    print("Error generating PDF")
else:
    print(f"Successfully generated PDF file: {pdf_path}")
