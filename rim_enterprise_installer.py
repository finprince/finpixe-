import json
import re
import base64
import gradio as gr
from openai import OpenAI

# --- 1. DYNAMIC SCHEMAS & FIREWALLS ---
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
    if not str(hsn).isdigit(): errors.append("HSN codes must be purely numeric.")
    gst = data.get("gst_number") or ""
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', str(gst).upper()):
        errors.append("GST number format invalid. Check for OCR noise in PAN section.")
    sub = data.get("subtotal") or 0
    tax = data.get("tax") or 0
    total = data.get("total") or 0
    try:
        if round(float(sub) + float(tax), 2) != round(float(total), 2):
            errors.append(f"Math Error: Subtotal ({sub}) + Tax ({tax}) != Total ({total}).")
    except Exception: errors.append("Math Error: Ensure amounts are numbers.")
    return errors

def bank_statement_firewall(data):
    errors = []
    if data.get("account_number") == "null": data["account_number"] = ""
    if data.get("ifsc_code") == "null": data["ifsc_code"] = ""
    acct = data.get("account_number") or ""
    acct_clean = str(acct).replace(" ", "").replace("-", "")
    if not acct_clean or not acct_clean.isdigit():
        errors.append("Account number must be numeric.")
    ifsc = data.get("ifsc_code") or ""
    if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', str(ifsc).replace(" ", "").upper()):
        errors.append(f"IFSC code '{ifsc}' is invalid. Must be 4 letters, 1 zero, 6 alphanumeric.")
    bal = data.get("closing_balance")
    if bal is None or str(bal).strip() in ["0", "null", ""]:
        errors.append("Closing balance is missing.")
    else:
        try: float(bal)
        except ValueError: errors.append("Closing balance must be a number.")
    return errors

FIREWALLS = {"Invoice": invoice_firewall, "Bank Statement": bank_statement_firewall}

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- 2. AUTHENTICATION & SETUP ---
def verify_and_save_key(provider, key):
    if not key:
        return "❌ Please enter an API key.", gr.update(visible=False), None
    try:
        # Dynamically test the provided key
        client = OpenAI(api_key=key)
        client.models.list()
        msg = f"✅ Success! Connected to {provider}. RIM Gateway is now active and routing traffic."
        # Unlock the Dashboard tab
        return msg, gr.update(visible=True), key
    except Exception as e:
        return f"❌ Authentication Failed. Check your key. Error: {e}", gr.update(visible=False), None

# --- 3. NEURO-SYMBOLIC LOOP (USING CUSTOMER KEY) ---
def process_fintech_ocr(image_path, doc_type, customer_api_key):
    if not customer_api_key:
        return "Error", "System not initialized. Please go to Setup tab.", ""
    if not image_path:
        return "Error", "No image provided.", ""
        
    # Dynamically initialize client using the CUSTOMER's key, not a hardcoded server key.
    client = OpenAI(api_key=customer_api_key)
    
    active_schema = SCHEMAS[doc_type]
    active_firewall = FIREWALLS[doc_type]
    base64_image = encode_image(image_path)
    attempt = 1
    feedback_history = []
    log_output = f"=== RIM GATEWAY ACTIVE (Using Customer Provided LLM) ===\n"
    
    while attempt <= 3:
        log_output += f"\n--- ATTEMPT {attempt} ---\n"
        log_output += f"[System 1] Routing pixels to external LLM provider...\n"
        prompt = f"""Extract data from this image into strict JSON matching this schema:
{json.dumps(active_schema, indent=2)}
Output ONLY valid JSON wrapped in a ```json block. If a field is not found, output an empty string ""."""
        if feedback_history:
            prompt += f"\n\n[SYSTEM 2 REJECTION WARNING]: Fix these mathematical errors:\n" + "\n".join(feedback_history)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                temperature=0.0
            )
            content = response.choices[0].message.content
            json_str = content
            match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if match: json_str = match.group(1)
            extracted_data = json.loads(json_str.strip())
            log_output += f"-> LLM Output: {json.dumps(extracted_data)}\n\n"
        except Exception as e:
            return "API Error", log_output + f"LLM Provider Error: {e}", ""

        log_output += "[System 2] Intercepting payload. Running Math & Logic Firewall...\n"
        current_errors = active_firewall(extracted_data)

        if not current_errors:
            log_output += f"-> [SUCCESS] Payload verified. Safe to push to database.\n"
            return json.dumps(extracted_data, indent=2), log_output, "Validation Successful."
        
        log_output += f"-> [ERROR BLOCKED]: {' | '.join(current_errors)}\n"
        log_output += "-> Blocking database write. Pushing error back to LLM.\n"
        feedback_history = current_errors
        attempt += 1

    return "Failed", log_output, "System 2 permanently blocked extraction."

# --- 4. GRADIO UI (ENTERPRISE INSTALLER) ---
with gr.Blocks(title="RIM Enterprise Setup", theme=gr.themes.Monochrome()) as app:
    # State variable to hold the customer's key securely in memory
    customer_key_state = gr.State(None)
    
    gr.Markdown("# 🛡️ RIM: Enterprise Deployment Gateway")
    
    with gr.Tabs():
        # TAB 1: INITIAL SETUP
        with gr.TabItem("1. Initial Setup (BYOK)"):
            gr.Markdown("### Bring Your Own Key (BYOK) Configuration")
            gr.Markdown("RIM runs completely locally on your server. We do not charge you for AI compute. Please select your preferred LLM provider and enter your API key to connect System 1.")
            
            with gr.Row():
                with gr.Column():
                    provider_dropdown = gr.Dropdown(choices=["OpenAI", "Anthropic Claude (Coming Soon)", "Local Offline Model (Coming Soon)"], value="OpenAI", label="Select LLM Provider")
                    api_key_input = gr.Textbox(label="Enter API Key", type="password", placeholder="sk-...")
                    setup_btn = gr.Button("Initialize RIM Gateway", variant="primary")
                    setup_status = gr.Textbox(label="Connection Status", interactive=False)
            
            gr.Markdown("*Note: Your API key is stored securely in your local server memory. RIM never transmits this key to our servers.*")

        # TAB 2: ACTIVE DASHBOARD (Locked by default)
        with gr.TabItem("2. RIM Active Dashboard") as dash_tab:
            dashboard_container = gr.Column(visible=False) # Hidden until setup succeeds
            
            with dashboard_container:
                gr.Markdown("### 🟢 RIM Gateway is Active and Monitoring Traffic")
                with gr.Row():
                    with gr.Column(scale=1):
                        doc_type_dropdown = gr.Dropdown(choices=["Invoice", "Bank Statement"], value="Bank Statement", label="Select Document Type")
                        img_input = gr.Image(type="filepath", label="Upload Document")
                        run_btn = gr.Button("Run Vision Extraction", variant="primary")
                        
                    with gr.Column(scale=2):
                        logs_output = gr.Textbox(label="Gateway Logs (System 1 vs System 2)", lines=15)
                        final_output = gr.Code(label="Verified Database Payload (JSON)", language="json")

    # Wire up the Setup Button
    setup_btn.click(fn=verify_and_save_key, inputs=[provider_dropdown, api_key_input], outputs=[setup_status, dashboard_container, customer_key_state])
    
    # Wire up the Dashboard Button
    run_btn.click(fn=process_fintech_ocr, inputs=[img_input, doc_type_dropdown, customer_key_state], outputs=[final_output, logs_output, gr.Textbox(visible=False)])

if __name__ == "__main__":
    print("[RIM Installer] Starting Enterprise Setup Dashboard...")
    app.launch(server_port=7862, share=False)
