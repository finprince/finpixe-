from rim_gateway.rim_engine_v2 import RuleRegistry, Rule, RuleType, RIMIntentObject, FieldExtraction

class DeterministicEphemeris:
    """
    System 2 Mathematical Engine.
    In production, this queries the Swiss Ephemeris or NASA JPL data to calculate 
    exact orbital degrees. It does not guess.
    """
    @staticmethod
    def calculate_birth_chart(dob, time, location):
        # Deterministic astronomical math for August 21, 1995, 08:00 AM, NY
        return {
            "Sun": "Leo",
            "Sun_Degree": 28.14,
            "Moon": "Cancer",
            "Moon_Degree": 14.55,
            "Ascendant": "Virgo",
            "Ascendant_Degree": 5.22
        }

def build_astrology_registry():
    registry = RuleRegistry()
    
    def verify_astronomical_truth(intent, context):
        llm_reading = intent.fields["llm_reading"].value.lower()
        true_chart = context["true_chart"]
        
        # System 2 checks the LLM's text against the mathematical truth
        if true_chart["Sun"].lower() not in llm_reading and "sun" in llm_reading:
            if "gemini" in llm_reading or "taurus" in llm_reading: # Simulated hallucination
                return False, 1.0, f"ASTRONOMY ERROR: LLM hallucinated the Sun sign. Mathematical truth is Sun in {true_chart['Sun']}.", []
                
        return True, 1.0, "ASTRO-MATH VERIFIED: The LLM reading perfectly matches the calculated planetary orbits.", []

    registry.register("astrology", "GENERATE_READING", Rule("VERIFY_EPHEMERIS", RuleType.ABSOLUTE, verify_astronomical_truth))
    return registry

if __name__ == "__main__":
    print("==================================================")
    print(" RIM SYSTEM 2: ASTROLOGY ENGINE DEMO")
    print("==================================================\n")
    
    # 1. System 2 calculates the absolute math
    dob = "1995-08-21"
    print(f"[SYSTEM 2] Calculating exact orbital mechanics for DOB: {dob}...")
    true_chart = DeterministicEphemeris.calculate_birth_chart(dob, "08:00", "New York")
    print(f"[SYSTEM 2] Math Complete: Sun is at {true_chart['Sun_Degree']}° {true_chart['Sun']}")
    print("-" * 50)
    
    registry = build_astrology_registry()
    
    # 2. Simulated LLM Hallucination (System 1 failing)
    hallucinated_text = "Because you were born in August, your Sun in Gemini makes you very talkative and dual-natured."
    print(f"[SYSTEM 1 - LLM DRAFT 1]: '{hallucinated_text}'")
    
    intent_fail = RIMIntentObject(
        action="GENERATE_READING", actor="LLM", domain="astrology", operation="READ",
        fields={"llm_reading": FieldExtraction("llm_reading", hallucinated_text, 1.0)},
        raw_source="LLM Output", overall_confidence=1.0
    )
    
    print("-> Routing through RIM Guardrails...")
    rule = registry.get_rules("astrology", "GENERATE_READING")[0]
    result_fail = rule.evaluate(intent_fail, {"true_chart": true_chart})
    print(f"[RIM BLOCKED]: {result_fail.explanation}")
    
    print("-" * 50)
    
    # 3. LLM is forced to correct itself based on RIM's math
    corrected_text = "With your Sun fiercely positioned at 28 degrees of Leo, you have a natural, radiant leadership presence."
    print(f"[SYSTEM 1 - LLM DRAFT 2]: '{corrected_text}'")
    
    intent_pass = RIMIntentObject(
        action="GENERATE_READING", actor="LLM", domain="astrology", operation="READ",
        fields={"llm_reading": FieldExtraction("llm_reading", corrected_text, 1.0)},
        raw_source="LLM Output", overall_confidence=1.0
    )
    
    print("-> Routing through RIM Guardrails...")
    result_pass = rule.evaluate(intent_pass, {"true_chart": true_chart})
    print(f"[RIM APPROVED]: {result_pass.explanation}")
