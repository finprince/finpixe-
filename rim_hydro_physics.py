from rim_gateway.rim_engine_v2 import RuleRegistry, Rule, RuleType, RIMIntentObject, FieldExtraction

def build_hydro_registry():
    registry = RuleRegistry()
    
    def calculate_bathroom_hydro(intent, context):
        flow_gpm = intent.fields["flow_gpm"].value
        pressure_psi = intent.fields["pressure_psi"].value
        efficiency = intent.fields["efficiency"].value
        
        # 1. System 2 Constraints (Household Pipe Limits)
        if flow_gpm > 5.0:
            return False, 1.0, f"PHYSICS ERROR: Standard bathroom pipe cannot exceed 5 GPM. Requested: {flow_gpm}", []
        
        # 2. Physics Conversions
        # Flow Rate (Q): Gallons per minute to Cubic meters per second (m^3/s)
        Q = flow_gpm * 0.00006309
        
        # Head (h): Pressure (PSI) to meters of water head
        # 1 PSI = 0.703 meters of head
        h = pressure_psi * 0.703
        
        # Constants
        rho = 1000  # Density of water (kg/m^3)
        g = 9.81    # Gravity (m/s^2)
        
        # 3. Absolute Power Equation: P = efficiency * rho * g * h * Q
        power_watts = efficiency * rho * g * h * Q
        
        return True, 1.0, f"Math Verified: Capable of generating exactly {power_watts:.2f} Watts of power.", []

    registry.register("physics", "CALCULATE_HYDRO", Rule("HYDRO_THERMODYNAMICS", RuleType.ABSOLUTE, calculate_bathroom_hydro))
    return registry

# Initialize RIM System 2
registry = build_hydro_registry()

# The intent: Generate power from a standard bathroom shower pipe
# Average shower flow = 2.5 GPM, Average City Pressure = 50 PSI, Micro-turbine efficiency = 60%
intent = RIMIntentObject(
    action="CALCULATE_HYDRO",
    actor="ENGINEER",
    domain="physics",
    operation="CALCULATE",
    fields={
        "flow_gpm": FieldExtraction("flow_gpm", 2.5, 1.0),
        "pressure_psi": FieldExtraction("pressure_psi", 50.0, 1.0),
        "efficiency": FieldExtraction("efficiency", 0.6, 1.0)
    },
    raw_source="Bathroom Pipe Generator",
    overall_confidence=1.0
)

print("==================================================")
print(" RIM SYSTEM 2 PHYSICS CALCULATION: BATHROOM HYDRO")
print("==================================================\n")

rules = registry.get_rules("physics", "CALCULATE_HYDRO")
for rule in rules:
    rule_result = rule.evaluate(intent, {})
    if not rule_result.passed:
        print(f"[BLOCKED] {rule_result.explanation}")
    else:
        print(f"[VERIFIED] {rule_result.explanation}")
