import json
import os
import re
import base64
import gradio as gr
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SCHEMAS = {
    "Invoice": {
        "vendor_name": "string",
        "gst_number": "string",
        "hsn_code": "string",
        "subtotal": "float",
        "tax": "float",
        "total": "float"
    },
    "Bank Statement": {
        "bank_name": "string",
        "account_number": "string",
        "ifsc_code": "string",
        "closing_balance": "float"
    }
}

def invoice_firewall(data):
    errors = []
    hsn = data.get("hsn_code") or ""
    if not str(hsn).isdigit():
        errors.append("HSN codes must be purely numeric. You extracted a letter.")
        
    gst = data.get("gst_number") or ""
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', str(gst).upper()):
        errors.append("GST number format invalid. Check for OCR noise in the PAN section.")
        
    sub = data.get("subtotal") or 0
    tax = data.get("tax") or 0
    total = data.get("total") or 0
    try:
        if round(float(sub) + float(tax), 2) != round(float(total), 2):
            errors.append(f"Math Error: Subtotal ({sub}) + Tax ({tax}) != Total ({total}).")
    except Exception:
        errors.append("Math Error: Ensure amounts are numbers.")
    return errors

def bank_statement_firewall(data):
    errors = []
    
    # Catch literal string "null" from LLM
    if data.get("account_number") == "null":
        data["account_number"] = ""
    if data.get("ifsc_code") == "null":
        data["ifsc_code"] = ""
        
    acct = data.get("account_number") or ""
    acct_clean = str(acct).replace(" ", "").replace("-", "")
    if not acct_clean or not acct_clean.isdigit():
        errors.append("Account number is missing or invalid. Look closely at the top right of the document for 'Account No'.")
        
    ifsc = data.get("ifsc_code") or ""
    ifsc_clean = str(ifsc).replace(" ", "")
    if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc_clean.upper()):
        errors.append(f"IFSC code '{ifsc}' is invalid. It must be 4 letters, 1 zero, and 6 alphanumeric chars. Look closely at the top right for 'IFSC'.")
        
    bal = data.get("closing_balance")
    if bal is None or str(bal).strip() == "0" or str(bal).strip() == "null":
        errors.append("Closing balance is missing. Look at the last row in the 'Closing Balance' column.")
    else:
        try:
            float(bal)
        except ValueError:
            errors.append("Closing balance must be a number.")
            
    return errors

FIREWALLS = {
    "Invoice": invoice_firewall,
    "Bank Statement": bank_statement_firewall
}

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_fintech_ocr(image_path, doc_type):
    if not image_path:
        return "Error", "No image provided.", ""
        
    active_schema = SCHEMAS[doc_type]
    active_firewall = FIREWALLS[doc_type]
    base64_image = encode_image(image_path)
    attempt = 1
    feedback_history = []
    log_output = f"=== RIM DYNAMIC MODE INITIATED: {doc_type.upper()} ===\n\n"
    
    while attempt <= 3:
        log_output += f"--- ATTEMPT {attempt} ---\n"
        log_output += f"[System 1] LLM Vision Engine scanning for {doc_type} fields...\n"
        
        prompt = f"""You are RIM System 1 (Vision). Look at the image and extract the data into strict JSON matching this schema:
{json.dumps(active_schema, indent=2)}
Output ONLY valid JSON wrapped in a ```json block. If a field is not found, output an empty string "" instead of null."""

        if feedback_history:
            prompt += f"\n\n[SYSTEM 2 REJECTION WARNING]: Your previous extraction failed our strict logic checks. Look VERY closely at the image and fix these errors:\n" + "\n".join(feedback_history)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
                ],
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            if not content:
                raise Exception("LLM returned empty content.")
                
            # Parse JSON manually to bypass OpenAI's strict json_object filter on PII images
            json_str = content
            match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                
            extracted_data = json.loads(json_str.strip())
            log_output += f"-> LLM Output: {json.dumps(extracted_data)}\n\n"
        except Exception as e:
            return "API Error", log_output + f"Vision API Error: {e}", ""

        # System 2 Validation
        log_output += "[System 2] Running Math & Logic Firewall...\n"
        current_errors = active_firewall(extracted_data)

        if not current_errors:
            log_output += f"-> [SUCCESS] Passed all {doc_type} bounds.\n"
            return json.dumps(extracted_data, indent=2), log_output, "Validation Successful."
        
        log_output += f"-> [ERROR BLOCKED]: {' | '.join(current_errors)}\n"
        log_output += "-> Pushing error back to LLM to force OCR correction from image.\n\n"
        
        feedback_history = current_errors
        attempt += 1

    return "Failed", log_output, "System 2 blocked extraction after 3 failed attempts."

with gr.Blocks(title="RIM Enterprise: Dynamic Vision OCR", theme=gr.themes.Monochrome()) as app:
    gr.Markdown("# 🏦 RIM Enterprise: Dynamic Document OCR")
    gr.Markdown("Upload an Invoice or a Bank Statement. Watch System 2 force the Vision Engine to correct itself if it misses an IFSC code or hallucinates a number.")
    
    with gr.Row():
        with gr.Column(scale=1):
            doc_type_dropdown = gr.Dropdown(choices=["Invoice", "Bank Statement"], value="Bank Statement", label="0. Select Document Type")
            img_input = gr.Image(type="filepath", label="1. Upload Messy Image/PDF screenshot")
            btn = gr.Button("Run Vision Extraction", variant="primary")
            
        with gr.Column(scale=2):
            logs_output = gr.Textbox(label="2. Neuro-Symbolic Loop Logs (System 1 vs System 2)", lines=15)
            final_output = gr.Code(label="3. Final Verified Database Payload (JSON)", language="json")

    btn.click(fn=process_fintech_ocr, inputs=[img_input, doc_type_dropdown], outputs=[final_output, logs_output, gr.Textbox(visible=False)])

if __name__ == "__main__":
    app.launch(server_port=7861, share=False)
