import markdown
import os

md_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.md"
html_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\cto_pitch.html"

# Read Markdown
with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Convert Markdown to HTML with extensions for tables and formatting
html = markdown.markdown(text, extensions=['tables', 'fenced_code'])

# Add professional CSS styling to make it look like a clean PDF/Presentation
css = """
<style>
    body {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
        background-color: #fcfcfc;
    }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    h2 { color: #2980b9; margin-top: 30px; }
    h3 { color: #16a085; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    th, td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    th { background-color: #34495e; color: white; }
    img { max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.3); margin: 20px 0; }
    blockquote {
        border-left: 5px solid #e74c3c;
        background-color: #f9f9f9;
        padding: 15px;
        margin: 20px 0;
        font-weight: bold;
    }
</style>
"""

# Build the final HTML document
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>RIM: CTO Pitch</title>
    {css}
</head>
<body>
    {html}
</body>
</html>
"""

# Write the HTML file
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"Successfully generated presentation file: {html_path}")
