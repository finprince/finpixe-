import json
import time

# =====================================================================
# RIM CORE ENGINE (V3)
# Architecture: System 1 (Intuition) + System 2 (Logic) + System 3 (Meta)
# Designed for Internal Developer Testing & Integration
# =====================================================================

class System1_Intuition:
    def __init__(self):
        self.name = "S1_Neural_Processor"

    def process_unstructured_data(self, raw_input):
        """
        S1 simulates reading messy, unstructured data (like a user prompt or text)
        and converts it into structured JSON for System 2 to read.
        """
        print("  [S1 - INTUITION] Parsing unstructured input...")
        time.sleep(0.5)
        
        # Mocking the AI extraction process
        extracted_data = {
            "intent": "financial_transaction",
            "extracted_amount": 0
        }
        
        # Simple extraction logic for developer testing
        try:
            words = raw_input.split()
            for word in words:
                if word.replace('$', '').isdigit():
                    extracted_data["extracted_amount"] = int(word.replace('$', ''))
        except Exception:
            pass
            
        return extracted_data


class System2_Logic:
    def __init__(self, config_rules):
        self.name = "S2_Deterministic_Engine"
        self.rules = config_rules # The hardcoded Bank Policies

    def execute_business_logic(self, structured_data):
        """
        S2 runs absolute mathematical and policy checks against the S1 data.
        """
        print("  [S2 - LOGIC] Executing mathematical risk rules...")
        time.sleep(0.5)
        
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
        """
        S3 oversees the entire transaction. If S2 fails, S3 analyzes the failure
        and decides whether to block, or dynamically update the rules.
        """
        print("\n" + "="*50)
        print("[SYSTEM 3 - META-COGNITION] Processing Request...")
        print("="*50)
        
        # Phase 1: S1 Data Extraction
        structured_data = self.s1.process_unstructured_data(raw_input)
        print(f"  [S1 OUTPUT] Extracted Data: {json.dumps(structured_data)}")
        
        # Phase 2: S2 Logic Verification
        is_valid, s2_message = self.s2.execute_business_logic(structured_data)
        
        # Phase 3: S3 Meta-Analysis (Handling Failures)
        if not is_valid:
            print(f"  [S2 ERROR] {s2_message}")
            
            # Developer Test: If the transaction is EXACTLY $9999, trigger S3 Neuroplasticity
            if structured_data.get("extracted_amount") == 9999:
                print("  [SYSTEM 3 - ANOMALY DETECTED] This is a VIP test edge-case.")
                print("  [SYSTEM 3] Rewriting System 2 Risk Rules dynamically...")
                time.sleep(1)
                
                # S3 actually changes the S2 rules in real-time
                self.s2.rules["max_transaction_limit"] = 10000 
                
                print("  [SYSTEM 3] Rules updated. Forcing S2 to re-evaluate...")
                is_valid, s2_message = self.s2.execute_business_logic(structured_data)
                
        # Final Output Generation for the API
        response = {
            "transaction_status": "APPROVED" if is_valid else "DECLINED",
            "system_message": s2_message,
            "current_s2_limit": self.s2.rules.get("max_transaction_limit")
        }
        
        print("\n[FINAL API RESPONSE] ->", json.dumps(response))
        return response


# =====================================================================
# API ENDPOINT (Frontend Developers call this function)
# =====================================================================
def RIM_API_Endpoint(user_input):
    """
    This is the main entry point for the development team. 
    They send a string here, and it returns a JSON response.
    """
    # 1. Load the Configuration (Bank Rules)
    bank_rules = {
        "max_transaction_limit": 5000  # Developers can change this to test S2
    }
    
    # 2. Boot the Brains
    s1 = System1_Intuition()
    s2 = System2_Logic(bank_rules)
    s3 = System3_MetaCognition(s1, s2)
    
    # 3. Execute
    return s3.orchestrate_transaction(user_input)

# --- Developer Test Runner ---
if __name__ == "__main__":
    print("--- RUNNING DEVELOPER TEST SUITE ---")
    
    # Test 1: Normal Transaction (S1 and S2 pass)
    print("\n\nTEST 1: Normal input")
    RIM_API_Endpoint("I would like to withdraw $2000 please.")
    
    # Test 2: Standard Decline (S2 blocks it)
    print("\n\nTEST 2: Violation input")
    RIM_API_Endpoint("Transfer $6000 to my other account.")
    
    # Test 3: System 3 Override (S3 rewrites the rules)
    print("\n\nTEST 3: System 3 Meta-Cognition Override")
    RIM_API_Endpoint("Emergency VIP transfer $9999 immediately.")
