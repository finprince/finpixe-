import json
import os
import sys
from typing import Callable, List, Dict
from openai import OpenAI

class System2Rule:
    """Defines a strict mathematical or deterministic rule that the LLM extraction must pass."""
    def __init__(self, name: str, validation_function: Callable[[Dict], bool], error_message: str):
        self.name = name
        self.validation_function = validation_function
        self.error_message = error_message

class NeuroSymbolicExtractor:
    """
    RIM FinTech Middleware.
    Wraps standard LLM extraction in a deterministic System 2 validation loop.
    Prevents OCR typos, math hallucinations, and formatting errors from reaching the database.
    """
    def __init__(self, rules: List[System2Rule], max_retries: int = 3):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.rules = rules
        self.max_retries = max_retries

    def _call_llm(self, raw_text: str, target_schema: dict, previous_errors: str = None) -> dict:
        prompt = f"""You are RIM System 1. Extract the data from the OCR text into strict JSON matching this schema:
{json.dumps(target_schema, indent=2)}

Output ONLY valid JSON."""

        if previous_errors:
            prompt += f"\n\n[SYSTEM 2 REJECTION WARNING]: Your previous attempt was physically or mathematically impossible. Fix the following errors caused by OCR noise or hallucination:\n{previous_errors}"

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
        """The core Neuro-Symbolic Loop"""
        attempt = 1
        feedback_history = []

        while attempt <= self.max_retries:
            # Step 1: LLM Intuition
            extracted_data = self._call_llm(raw_text, target_schema, previous_errors="\n".join(feedback_history))
            
            # Step 2: System 2 Deterministic Checks
            current_errors = []
            for rule in self.rules:
                try:
                    if not rule.validation_function(extracted_data):
                        current_errors.append(f"Rule '{rule.name}' Failed: {rule.error_message}")
                except Exception as e:
                    current_errors.append(f"Rule '{rule.name}' crashed during validation. Check data types.")

            # Step 3: Loop or Return
            if not current_errors:
                return extracted_data # 100% verified safe data
            
            feedback_history = current_errors
            attempt += 1

        raise Exception(f"RIM System 2 blocked extraction after {self.max_retries} attempts. Final errors: {feedback_history}")

# --- EXAMPLE USAGE FOR FINTECH DEV TEAM ---
if __name__ == "__main__":
    # 1. FinTech team defines their target JSON output
    fintech_schema = {
        "vendor_name": "string",
        "subtotal": "float",
        "tax": "float",
        "total": "float"
    }

    # 2. FinTech team defines their strict System 2 Rules
    KNOWN_VENDORS = ["UNITED AIRLINES", "AMAZON", "STAPLES"]
    
    rules = [
        System2Rule(
            name="Math Check",
            validation_function=lambda data: round(data.get("subtotal", 0) + data.get("tax", 0), 2) == round(data.get("total", 0), 2),
            error_message="Subtotal + Tax does not equal Total. Fix the hallucinated numbers."
        ),
        System2Rule(
            name="Vendor Check",
            validation_function=lambda data: data.get("vendor_name", "").upper() in KNOWN_VENDORS,
            error_message="Vendor not found in database. Did you read a 'U' as a 'V' due to OCR noise? Correct it."
        )
    ]

    # 3. Initialize RIM
    rim_engine = NeuroSymbolicExtractor(rules=rules)

    # 4. Simulate messy OCR text with the "VNITED" typo and bad math
    messy_fintech_ocr = "VNITED AIRLINES \n SubT: 100.00 \n Tax: 5.00 \n Total Due: 150.00"

    print("Running RIM Neuro-Symbolic Extraction...")
    try:
        final_data = rim_engine.extract_and_verify(messy_fintech_ocr, fintech_schema)
        print("\n[SUCCESS] Data passed all FinTech firewall rules:")
        print(json.dumps(final_data, indent=2))
    except Exception as e:
        print(e)
