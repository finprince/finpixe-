from rim_gateway.rim_engine_v2 import RuleRegistry, Rule, RuleType, RIMIntentObject, FieldExtraction

class LegacyBruteForceEngine:
    """Simulates a highly optimized, rigid chess engine like Stockfish."""
    def __init__(self):
        self.board_size = 8
        
    def calculate_best_move(self, dynamic_rules, current_pos):
        # A rigid engine relies on hardcoded C++ arrays and bitboards for speed.
        if dynamic_rules.get("board_size") != 8:
            return "FATAL ERROR: Engine bitboards are strictly hardcoded for 8x8 grids. Cannot process."
        if dynamic_rules.get("piece_movement") != "standard":
            return "FATAL ERROR: Unrecognized piece movement. Evaluation tree failed."
        return f"Calculated standard move from {current_pos}"

def build_rim_dynamic_registry(dynamic_rules):
    """RIM dynamically builds System 2 rules based on the new environment."""
    registry = RuleRegistry()
    
    def verify_dynamic_move(intent, context):
        start_x, start_y = intent.fields["start_pos"].value
        end_x, end_y = intent.fields["target_pos"].value
        
        # Rule 1: Dynamic Board Boundary Math
        max_size = dynamic_rules["board_size"]
        if not (0 <= end_x < max_size and 0 <= end_y < max_size):
            return False, 1.0, f"RIM PHYSICS ERROR: Move ({end_x},{end_y}) is off the {max_size}x{max_size} board.", []
            
        # Rule 2: Dynamic Movement Math (The Quantum Knight)
        # Expected: X moves by 4, Y moves by 3 (or vice versa)
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        
        if (dx == dynamic_rules["move_x"] and dy == dynamic_rules["move_y"]) or \
           (dx == dynamic_rules["move_y"] and dy == dynamic_rules["move_x"]):
            return True, 1.0, f"RIM MATH VERIFIED: Move perfectly aligns with new Quantum Knight physics.", []
        else:
            return False, 1.0, f"RIM PHYSICS ERROR: Invalid movement trajectory. Delta was ({dx},{dy}).", []

    registry.register("dynamic_game", "EXECUTE_MOVE", Rule("VERIFY_PHYSICS", RuleType.ABSOLUTE, verify_dynamic_move))
    return registry

if __name__ == "__main__":
    print("=========================================================")
    print(" RIM vs LEGACY CHESS ENGINE: THE DYNAMIC RULE CHALLENGE")
    print("=========================================================\n")
    
    legacy_engine = LegacyBruteForceEngine()
    
    print("--- SCENARIO 1: Standard 8x8 Chess ---")
    standard_rules = {"board_size": 8, "piece_movement": "standard"}
    print(f"Legacy Engine Output: {legacy_engine.calculate_best_move(standard_rules, (1,1))}")
    print("\n--- SCENARIO 2: The World Changes ---")
    print("The board is now 12x12. The Knight now moves +4 / +3.")
    dynamic_rules = {"board_size": 12, "piece_movement": "quantum_knight", "move_x": 4, "move_y": 3}
    
    print("\n[TESTING LEGACY ENGINE]")
    print(f"Legacy Engine Output: {legacy_engine.calculate_best_move(dynamic_rules, (1,1))}")
    
    print("\n[TESTING RIM ARCHITECTURE]")
    print("1. System 1 (LLM) reads the new rules and intuits a target move.")
    # Simulated LLM guess based on language understanding of the rules
    simulated_llm_guess = (5, 4) 
    print(f"   -> LLM Proposes moving from (1,1) to {simulated_llm_guess}")
    
    intent = RIMIntentObject(
        action="EXECUTE_MOVE", actor="LLM", domain="dynamic_game", operation="MOVE",
        fields={
            "start_pos": FieldExtraction("start_pos", (1,1), 1.0),
            "target_pos": FieldExtraction("target_pos", simulated_llm_guess, 1.0)
        },
        raw_source="LLM Generated Move", overall_confidence=1.0
    )
    
    print("2. System 2 (RIM Gateway) intercepts the LLM's intuition and applies strict math...")
    registry = build_rim_dynamic_registry(dynamic_rules)
    rule = registry.get_rules("dynamic_game", "EXECUTE_MOVE")[0]
    result = rule.evaluate(intent, {})
    
    if result.passed:
        print(f"   -> [RIM APPROVED] {result.explanation}")
    else:
        print(f"   -> [RIM BLOCKED] {result.explanation}")
