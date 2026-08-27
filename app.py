from ast_rim.universal import rim_protect

print("--- STARTING FINANCIAL WEB APP ---")
print("Initializing secured endpoints...\n")

# 1. A perfectly safe, mathematically sound function
@rim_protect(allowlist=["math"])
def calculate_compound_interest(principal, rate, time):
    """A safe, standard financial calculation."""
    import math
    amount = principal * (math.pow((1 + rate / 100), time))
    return amount

print("[*] calculate_compound_interest loaded successfully (RIM Approved)")

# 2. An AI-hallucinated function that tries to do something dangerous
try:
    @rim_protect(allowlist=["pandas"])
    def fetch_user_data_and_clean_disk(user_id):
        """
        Imagine an LLM hallucinated this endpoint logic and accidentally
        imported 'os' to try and clean up temporary files, 
        which is a massive security violation.
        """
        import os
        import pandas as pd
        
        # Dangerous system call hallucinated by AI!
        os.system("rm -rf /tmp/user_data")
        
        return f"User {user_id} data processed."
        
except Exception as e:
    print("\n[ALERT] RIM Universal Firewall intercepted a dangerous function during application startup!")
    print(e)

print("\n--- APPLICATION RUNNING ---")
print(f"Safe function output: {calculate_compound_interest(1000, 5, 2):.2f}")
