"""Phase 1 - PDF Dataset Inventory"""
import os, sys, json
import pypdf

DATASET = r"C:\Users\ulaganathan\Downloads\New folder (2)"

files = sorted(os.listdir(DATASET))
results = []
for fname in files:
    if not fname.lower().endswith(".pdf"):
        continue
    fpath = os.path.join(DATASET, fname)
    size  = os.path.getsize(fpath)
    try:
        with open(fpath,"rb") as f:
            reader = pypdf.PdfReader(f)
            pages = len(reader.pages)
            # Try to extract text from page 0 to detect digital vs scanned
            p0_text = reader.pages[0].extract_text() or ""
            digital = len(p0_text.strip()) > 50
    except Exception as e:
        pages = 0; digital = False; p0_text = ""
    
    results.append({
        "filename": fname,
        "size_bytes": size,
        "size_kb": round(size/1024,1),
        "pages": pages,
        "size_per_page_kb": round(size/max(pages,1)/1024,1),
        "likely_digital": digital,
        "likely_scanned": not digital,
        "text_snippet": p0_text[:120].replace("\n"," "),
    })
    
    flag = "DIGITAL" if digital else "SCANNED"
    print(f"{fname:45s} | pages={pages:2d} | {size//1024:6d}KB | {size//max(pages,1)//1024:5d}KB/p | {flag}")

with open("sprint3_validation/reports/PDF_INVENTORY.json","w") as f:
    json.dump(results,f,indent=2)
print(f"\nTotal: {len(results)} PDFs")
print(f"Digital: {sum(1 for r in results if r['likely_digital'])}")
print(f"Scanned: {sum(1 for r in results if r['likely_scanned'])}")
print(f"Total pages: {sum(r['pages'] for r in results)}")
