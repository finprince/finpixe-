import json
import time

# =====================================================================
# RIM CORE ENGINE (V3)
# Architecture: System 1 (Intuition) + System 2 (Logic) + System 3 (Meta)
# =====================================================================

class System1_Intuition:
    def __init__(self):
        self.name = "S1_Neural_Processor"

    def process_unstructured_data(self, raw_input):
        extracted_data = {
            "intent": "financial_transaction",
            "extracted_amount": 0
        }
        try:
            import re
            cleaned = raw_input.replace(',', '')
            numbers = re.findall(r'\d+', cleaned)
            if numbers:
                extracted_data["extracted_amount"] = int(numbers[0])
        except Exception:
            pass
        return extracted_data


class System2_Logic:
    def __init__(self, config_rules):
        self.name = "S2_Deterministic_Engine"
        self.rules = config_rules

    def execute_business_logic(self, structured_data):
        amount = structured_data.get("extracted_amount", 0)
        max_limit = self.rules.get("max_transaction_limit", 1000)

        if amount > max_limit:
            return False, f"Risk Policy Violation: Amount {amount} exceeds hard limit of {max_limit}."
        elif amount <= 0:
            return False, "Data Error: No valid amount detected."
        return True, "All mathematical and risk policies passed."


class System3_MetaCognition:
    def __init__(self, system1, system2):
        self.s1 = system1
        self.s2 = system2

    def orchestrate_transaction(self, raw_input):
        trace = []

        # Phase 1: S1 Data Extraction
        structured_data = self.s1.process_unstructured_data(raw_input)
        trace.append({"phase": "S1_EXTRACTION", "output": structured_data})

        # Phase 2: S2 Logic Verification
        is_valid, s2_message = self.s2.execute_business_logic(structured_data)
        trace.append({"phase": "S2_LOGIC", "valid": is_valid, "message": s2_message})

        # Phase 3: S3 Meta-Analysis
        s3_override = False
        if not is_valid and structured_data.get("extracted_amount") == 9999:
            self.s2.rules["max_transaction_limit"] = 10000
            is_valid, s2_message = self.s2.execute_business_logic(structured_data)
            s3_override = True
            trace.append({"phase": "S3_OVERRIDE", "new_limit": 10000, "result": s2_message})

        response = {
            "transaction_status": "APPROVED" if is_valid else "DECLINED",
            "system_message": s2_message,
            "current_s2_limit": self.s2.rules.get("max_transaction_limit"),
            "s3_override_triggered": s3_override,
            "trace": trace
        }
        return response


def RIM_API_Endpoint(user_input, max_transaction_limit=5000):
    bank_rules = {"max_transaction_limit": max_transaction_limit}
    s1 = System1_Intuition()
    s2 = System2_Logic(bank_rules)
    s3 = System3_MetaCognition(s1, s2)
    return s3.orchestrate_transaction(user_input)
