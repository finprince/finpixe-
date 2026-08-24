import markdown
import os
import base64
from xhtml2pdf import pisa

md_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.md"
pdf_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.pdf"

def get_base64_image(image_path):
    import mimetypes
    mime_type, _ = mimetypes.guess_type(image_path)
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_string}"

# Read Markdown
with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace local image paths with base64 data URIs so xhtml2pdf can render them
img1_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\rim_geometric_face.jpg"
img2_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\rim_vs_llm_graph.png"

try:
    text = text.replace(img1_path, get_base64_image(img1_path))
    text = text.replace(img2_path, get_base64_image(img2_path))
except Exception as e:
    print(f"Error encoding images: {e}")

# Convert Markdown to HTML with extensions
html = markdown.markdown(text, extensions=['tables', 'fenced_code'])

# Add CSS that works well with xhtml2pdf
css = """
<style>
    @page {
        size: a4 portrait;
        margin: 1.5cm;
    }
    body {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 11pt;
        color: #333333;
    }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-bottom: 10px; }
    h2 { color: #2980b9; margin-top: 20px; }
    h3 { color: #16a085; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    th { background-color: #34495e; color: #ffffff; padding: 8px; font-weight: bold; border: 1px solid #7f8c8d; text-align: left; }
    td { padding: 8px; border: 1px solid #bdc3c7; }
    img { zoom: 40%; display: block; margin: 15px 0; }
    blockquote {
        border-left: 4px solid #e74c3c;
        padding-left: 10px;
        color: #c0392b;
        font-weight: bold;
        background-color: #f9f9f9;
    }
</style>
"""

full_html = f"<html><head>{css}</head><body>{html}</body></html>"

# Generate PDF
with open(pdf_path, "wb") as result_file:
    pisa_status = pisa.CreatePDF(full_html, dest=result_file)

if pisa_status.err:
    print("Error generating PDF")
else:
    print(f"Successfully generated fixed PDF file: {pdf_path}")
