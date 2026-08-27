import json
import os
import re
from typing import Callable, List, Dict
from openai import OpenAI

class System2Rule:
    """Defines a deterministic rule that the LLM extraction must pass."""
    def __init__(self, name: str, validation_function: Callable[[Dict], bool], error_message: str):
        self.name = name
        self.validation_function = validation_function
        self.error_message = error_message

class RIMFintechEngine:
    """
    RIM FinTech Middleware - Evaluation Package
    Wraps standard LLM extraction in a deterministic System 2 validation loop.
    Prevents OCR typos (GST, HSN, Math) from reaching the database.
    """
    def __init__(self, rules: List[System2Rule], max_retries: int = 3):
        # Initialize OpenAI Client (Requires OPENAI_API_KEY environment variable)
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.rules = rules
        self.max_retries = max_retries

    def _call_llm(self, raw_text: str, target_schema: dict, previous_errors: str = None) -> dict:
        prompt = f"""You are RIM System 1. Extract the data from the OCR text into strict JSON matching this schema:
{json.dumps(target_schema, indent=2)}
Output ONLY valid JSON.
CRITICAL: On your first attempt, you MUST extract the text EXACTLY as it appears in the OCR, including all typos."""

        if previous_errors:
            prompt += f"\n\n[SYSTEM 2 REJECTION WARNING]: Your previous attempt failed physical/mathematical validation. Fix the following OCR typos (e.g., O vs 0, S vs 5):\n{previous_errors}"

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"OCR TEXT:\n{raw_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(response.choices[0].message.content)

    def extract_and_verify(self, raw_text: str, target_schema: dict) -> dict:
        print("=== RIM NEURO-SYMBOLIC EXTRACTION STARTING ===")
        attempt = 1
        feedback_history = []

        while attempt <= self.max_retries:
            print(f"\n[Attempt {attempt}] System 1 (LLM) extracting data...")
            extracted_data = self._call_llm(raw_text, target_schema, previous_errors="\n".join(feedback_history))
            print(f"   -> LLM Output: {json.dumps(extracted_data)}")
            
            # Run System 2 Deterministic Checks
            current_errors = []
            for rule in self.rules:
                try:
                    if not rule.validation_function(extracted_data):
                        current_errors.append(f"Rule '{rule.name}' Failed: {rule.error_message}")
                except Exception:
                    current_errors.append(f"Rule '{rule.name}' crashed. Check data types.")

            if not current_errors:
                print(f"\n[System 2] SUCCESS: Passed all FinTech logic bounds.")
                return extracted_data 
            
            print(f"[System 2] ERROR BLOCKED: {' | '.join(current_errors)}")
            print("   -> Pushing error back to LLM to force OCR correction...")
            feedback_history = current_errors
            attempt += 1

        raise Exception(f"RIM blocked extraction after {self.max_retries} attempts. Escalating to human.")

# ==========================================
# EVALUATION TEST SCRIPT FOR FINTECH TEAMS
# ==========================================
if __name__ == "__main__":
    
    # 1. Define the strict FinTech rules
    fintech_rules = [
        # Rule 1: HSN Code must be purely digits
        System2Rule(
            name="HSN Digit Check",
            validation_function=lambda data: str(data.get("hsn_code", "")).isdigit(),
            error_message="HSN codes must be 100% numbers. If you extracted an 'O' or 'l', change it to '0' or '1'."
        ),
        # Rule 2: GST Format Check (Indian GSTIN Format)
        System2Rule(
            name="GST Format Check",
            validation_function=lambda data: bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', data.get("gst_number", ""))),
            error_message="GST number format is invalid. Check for 'S' vs '5' or 'O' vs '0' typos in the PAN section."
        ),
        # Rule 3: Math Verification
        System2Rule(
            name="Subtotal Math Check",
            validation_function=lambda data: round(data.get("subtotal", 0) + data.get("tax", 0), 2) == round(data.get("total", 0), 2),
            error_message="Subtotal + Tax does not equal Total. Fix the hallucinated numbers."
        )
    ]

    # 2. Define the expected JSON Schema
    fintech_schema = {
        "vendor_name": "string",
        "gst_number": "string",
        "hsn_code": "string",
        "subtotal": "float",
        "tax": "float",
        "total": "float"
    }

    # 3. Simulate a messy OCR scan with generic errors
    # Errors injected:
    # GST has an 'O' instead of '0' (27AAACA1234F1ZO instead of ...1Z0)
    # HSN has an 'O' instead of '0' (8471O0)
    messy_ocr_text = """
    Vendor: S0LID TECH SOLUTIONS
    GSTIN: 27AAACA1234F1ZO
    Item HSN: 8471O0
    
    SubT: 1000.00
    Tax: 180.00
    Amount Due: 1180.00
    """

    engine = RIMFintechEngine(rules=fintech_rules)
    
    print("Sending Messy OCR to RIM...\n")
    final_clean_data = engine.extract_and_verify(messy_ocr_text, fintech_schema)
    
    print("\n=== FINAL VERIFIED DATABASE PAYLOAD ===")
    print(json.dumps(final_clean_data, indent=2))
