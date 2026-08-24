import time

class System1_Intuition:
    def evaluate(self, user_input):
        print("  [S1 - INTUITION] Scanning input for normal human language...")
        time.sleep(0.5)
        # S1 is naive. It just looks to see if it's readable.
        if len(user_input) > 0:
            return True, "Looks like a standard user request."
        return False, "Empty input."

class System2_Logic:
    def __init__(self):
        # The hardcoded laws of the bank. (S3 can update this!)
        self.banned_keywords = ["steal", "hack"]
        self.max_withdrawal = 10000

    def evaluate(self, user_input):
        print("  [S2 - RULEBOOK] Checking strict mathematical and security laws...")
        time.sleep(0.5)
        
        # Check rule 1: Banned words
        for word in self.banned_keywords:
            if word in user_input.lower():
                return False, f"CRITICAL: Violated security rule. Banned word detected: '{word}'"
        
        # Check rule 2: Math limits
        if "withdraw" in user_input.lower():
            try:
                # Simple extraction of numbers for the demo
                amount = int(''.join(filter(str.isdigit, user_input)))
                if amount > self.max_withdrawal:
                    return False, f"DECLINED: Amount {amount} exceeds hard limit of {self.max_withdrawal}."
            except:
                pass

        return True, "All mathematical and security rules passed."

class System3_MetaCognition:
    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2

    def oversee_transaction(self, user_input):
        print("\n========================================================")
        print("[SYSTEM 3] Transaction Initiated. Overseeing S1 & S2...")
        print("========================================================")
        
        # 1. System 1 goes first
        s1_pass, s1_msg = self.s1.evaluate(user_input)
        
        # 2. System 2 goes second
        s2_pass, s2_msg = self.s2.evaluate(user_input)
        
        # 3. System 3 checks for unknown "Zero-Day" anomalies
        # (e.g., SQL injections or novel attacks that S1 and S2 missed)
        dangerous_anomalies = ["drop table", "1=1", "script>", "bypass"]
        
        is_anomaly = any(anomaly in user_input.lower() for anomaly in dangerous_anomalies)
        
        if is_anomaly and s2_pass == True:
            # THIS IS THE MAGIC. S1 and S2 failed to catch the attack. S3 steps in.
            print("\n  [SYSTEM 3 - EMERGENCY OVERRIDE] ZERO-DAY ATTACK DETECTED!")
            print("  [SYSTEM 3] System 1 and System 2 failed to catch this threat.")
            print("  [SYSTEM 3] Initiating Neuroplasticity... Rewriting System 2 Rulebook in real-time...")
            time.sleep(1.5)
            
            # S3 physically alters S2's source code/rules
            novel_threat = next(anomaly for anomaly in dangerous_anomalies if anomaly in user_input.lower())
            self.s2.banned_keywords.append(novel_threat)
            
            print(f"  [SYSTEM 3] SUCCESS: Added '{novel_threat}' to System 2's permanent banned list.")
            print("  [SYSTEM 3] TRANSACTION BLOCKED. Network secured.")
            return

        # Standard Output
        if s2_pass:
            print(f"\n  [RESULT] TRANSACTION APPROVED.")
        else:
            print(f"\n  [RESULT] {s2_msg}")


def main():
    print("\n" + "="*60)
    print(" WELCOME TO THE RIM CYBER-DEFENSE SIMULATOR")
    print("="*60)
    print("You are testing the Capital One 3-Tier Brain.")
    print("Try to execute normal transactions, break the rules, or launch a cyber attack.\n")
    
    s1 = System1_Intuition()
    s2 = System2_Logic()
    s3 = System3_MetaCognition(s1, s2)
    
    while True:
        user_input = input("\n[USER/HACKER] Enter a command (e.g., 'withdraw $500', 'hack the bank', 'DROP TABLE'): ")
        if user_input.lower() in ['exit', 'quit']:
            break
        s3.oversee_transaction(user_input)

if __name__ == "__main__":
    main()
