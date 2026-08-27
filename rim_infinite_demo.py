from rim_gateway.rim_engine_v2 import RuleRegistry, Rule, RuleType
from rim_gateway.rim_infinite_generator import InfinitePermutationEngine
from rim_gateway.rim_engine_v2 import RuleResult

# 1. System 2 Rules (Physics & Logic)
def build_registry():
    registry = RuleRegistry()
    
    def check_material_feasibility(intent, context):
        material = intent.fields["material"].value
        pattern = intent.fields["pattern"].value
        
        # Physics Rule: You cannot carve a complex 'Voronoi' pattern into 'Bone' because it shatters.
        if material == "Bone" and pattern == "Voronoi":
            return False, 1.0, "Material physics violation: Bone shatters under Voronoi milling.", []
        return True, 1.0, "Material physics valid.", []

    registry.register("manufacturing", "GENERATE_CATALOG", Rule("MATERIAL_PHYSICS", RuleType.ABSOLUTE, check_material_feasibility))
    return registry

if __name__ == "__main__":
    print("=======================================================")
    print("  RIM INFINITE PERMUTATION ENGINE DEMO")
    print("=======================================================\n")
    
    # 2. The Seed provided by the LLM (System 1)
    llm_seed = {
        "material": ["Obsidian", "Quartz", "Bone", "Ceramic"],
        "pattern": ["Voronoi", "Spiral", "Smooth"],
        "color": ["Gold", "Blue", "Black"],
        "size_cm": [5.0, 7.5, 10.0]
    }
    
    # 3. RIM takes over to generate the dataset
    generator = InfinitePermutationEngine("manufacturing", "GENERATE_CATALOG", build_registry())
    result = generator.generate_dataset(llm_seed)
    
    print("\n[SAMPLE OF VALID DATASET OUTPUTS]:")
    for item in result["valid_dataset"][:5]:
        print(f"  -> {item}")
