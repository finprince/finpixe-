import random
import math
from rim_gateway.rim_engine_v2_1 import RIMEngineV2
from rim_gateway.rim_engine_v2 import ContextLoader, RuleRegistry, Rule, RuleType
from rim_gateway.rim_discovery import AlgorithmicIntuitionEngine, DiscoveryEngine

# ---------------------------------------------------------
# THE CHALLENGE: Discover a novel cup geometry 
# It must hold exactly 300ml, and the radius must be between 3 and 4 cm.
# ---------------------------------------------------------

# 1. The Mutator Function (Evolution)
def geometry_mutator(current_state: dict, correction_context: str) -> dict:
    # If no state exists yet, initialize a random guess
    if not current_state:
        return {"radius_cm": 1.0, "height_cm": 1.0}
    
    # Evolve the state based on random mutation
    # In a real neural/genetic algorithm, this uses gradients. Here we use random walk.
    return {
        "radius_cm": current_state["radius_cm"] + random.uniform(-0.5, 0.5),
        "height_cm": current_state["height_cm"] + random.uniform(-2.0, 2.0)
    }

# 2. System 2: The Physics Laws
def build_physics_registry() -> RuleRegistry:
    registry = RuleRegistry()

    def check_volume(intent, context):
        r = intent.fields["radius_cm"].value
        h = intent.fields["height_cm"].value
        
        # Physical constraints (no negative dimensions)
        if r <= 0 or h <= 0:
            return False, 1.0, "Physical impossibility (negative dimension)", []
            
        volume = math.pi * (r**2) * h
        
        # Target is exactly 300ml (with 1ml tolerance)
        if abs(volume - 300.0) < 1.0:
            return True, 1.0, f"Volume is {volume:.2f}ml", []
        return False, 1.0, f"Volume {volume:.2f}ml != 300ml", ["radius_cm", "height_cm"]

    def check_ergonomics(intent, context):
        r = intent.fields["radius_cm"].value
        # Cup must fit in a human hand (radius between 3 and 4 cm)
        if 3.0 <= r <= 4.0:
            return True, 1.0, f"Radius {r:.2f}cm is ergonomic", []
        return False, 1.0, f"Radius {r:.2f}cm is not ergonomic", ["radius_cm"]

    registry.register("geometry", "DESIGN_CUP", Rule("TARGET_VOLUME", RuleType.ABSOLUTE, check_volume))
    registry.register("geometry", "DESIGN_CUP", Rule("ERGONOMIC_GRIP", RuleType.ABSOLUTE, check_ergonomics))
    
    return registry

if __name__ == "__main__":
    print("=======================================================")
    print("  RIM DISCOVERY ENGINE  EVOLVING A NOVEL GEOMETRY")
    print("=======================================================\n")
    
    # Plug the Algorithmic Intuition into the RIM Engine
    intuition = AlgorithmicIntuitionEngine("geometry", "DESIGN_CUP", "TRANSFORM", geometry_mutator)
    engine = RIMEngineV2(intuition, ContextLoader(), build_physics_registry())
    
    # Wrap it in the Discovery Loop
    discovery = DiscoveryEngine(engine, max_iterations=50000)
    
    # Start the search from a 1cm x 1cm seed
    result = discovery.discover(seed_state={"radius_cm": 1.0, "height_cm": 1.0})
    
    if result["status"] == "DISCOVERED":
        r = result['solution']['radius_cm']
        h = result['solution']['height_cm']
        v = math.pi * (r**2) * h
        print("\n[NOVEL GEOMETRY DISCOVERED]")
        print(f"Radius : {r:.3f} cm")
        print(f"Height : {h:.3f} cm")
        print(f"Volume : {v:.3f} ml")
        print(f"Audit Proof Hash: {result['audit_hash']}")
