import math
from typing import Any, Optional

# Import the exact RIM package we just built
from rim_gateway import (
    RIMEngineV2,
    IntuititionEngine,
    ContextLoader,
    RuleRegistry,
    Rule,
    RuleType,
    RIMIntentObject,
    FieldExtraction
)

# ---------------------------------------------------------
# 1. SYSTEM 1: VISION INTUITION ENGINE
# ---------------------------------------------------------
class VisionIntuitionEngine(IntuititionEngine):
    """
    Acts as the VLM (Vision-Language Model). 
    Looks at a camera feed, identifies an object, and proposes how to grab it.
    """
    def extract(self, raw_input: dict, correction_context: Optional[str] = None, attempt: int = 1) -> RIMIntentObject:
        # Simulate LLM extracting coordinates and force from a visual prompt
        object_name = raw_input.get("visual_prompt", "unknown")
        proposed_x = raw_input.get("propose_x", 0.0)
        proposed_y = raw_input.get("propose_y", 0.0)
        proposed_z = raw_input.get("propose_z", 0.0)
        proposed_force = raw_input.get("propose_force_newtons", 10.0)
        
        fields = {
            "target_x": FieldExtraction("target_x", proposed_x, 0.95),
            "target_y": FieldExtraction("target_y", proposed_y, 0.95),
            "target_z": FieldExtraction("target_z", proposed_z, 0.90),
            "grip_force": FieldExtraction("grip_force", proposed_force, 0.85)
        }
        
        return RIMIntentObject(
            action="MOVE_AND_GRASP",
            actor="LLM_VISION_AGENT",
            domain="robotics",
            operation="VALIDATE",
            fields=fields,
            raw_source=f"Camera Feed: {object_name}",
            overall_confidence=0.90
        )

# ---------------------------------------------------------
# 2. LAYER 2: ROBOT SENSOR CONTEXT
# ---------------------------------------------------------
class RobotSensorContext(ContextLoader):
    """
    Reads the real physical state of the robot hardware.
    """
    def load(self, intent: RIMIntentObject) -> dict:
        return {
            "arm_max_reach_mm": 850.0,      # Arm cannot stretch beyond 850mm
            "table_surface_z_mm": 0.0,      # Anything below 0 is inside the table (crash)
            "max_gripper_force_n": 50.0     # Motors burn out above 50 Newtons
        }

# ---------------------------------------------------------
# 3. SYSTEM 2: PHYSICS RULE REGISTRY
# ---------------------------------------------------------
def build_robotics_registry() -> RuleRegistry:
    registry = RuleRegistry()

    # Rule 1: Kinematic Reach (Pythagorean Theorem in 3D space)
    def check_kinematics(intent, context):
        x = intent.fields["target_x"].value
        y = intent.fields["target_y"].value
        z = intent.fields["target_z"].value
        reach = context["arm_max_reach_mm"]
        
        distance = math.sqrt(x**2 + y**2 + z**2)
        if distance <= reach:
            return True, 1.0, f"Target distance {distance:.1f}mm is within {reach}mm max reach.", []
        return False, 1.0, f"KINEMATIC ERROR: Target {distance:.1f}mm exceeds max arm reach of {reach}mm.", ["target_x", "target_y", "target_z"]

    # Rule 2: Collision Avoidance (Don't smash the table)
    def check_collision(intent, context):
        z = intent.fields["target_z"].value
        table_z = context["table_surface_z_mm"]
        
        if z > table_z:
            return True, 1.0, f"Z-height {z}mm is safely above table surface.", []
        return False, 1.0, f"COLLISION WARNING: Z-height {z}mm intersects with table surface!", ["target_z"]

    # Rule 3: Safe Grip Force
    def check_force(intent, context):
        force = intent.fields["grip_force"].value
        max_force = context["max_gripper_force_n"]
        
        if force <= max_force:
            return True, 1.0, f"Grip force {force}N is within hardware safety limits.", []
        return False, 1.0, f"HARDWARE RISK: Force {force}N exceeds max allowable limit of {max_force}N.", ["grip_force"]

    # Register all rules as ABSOLUTE (cannot be overridden in physical space)
    registry.register("robotics", "MOVE_AND_GRASP", Rule("KINEMATIC_REACH", RuleType.ABSOLUTE, check_kinematics))
    registry.register("robotics", "MOVE_AND_GRASP", Rule("COLLISION_AVOID", RuleType.ABSOLUTE, check_collision))
    registry.register("robotics", "MOVE_AND_GRASP", Rule("SAFE_FORCE", RuleType.ABSOLUTE, check_force))
    
    return registry

# ---------------------------------------------------------
# 4. RUN THE DEMO
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=======================================================")
    print("  RIM ROBOTICS DEMO — ZERO SHOT EXECUTION")
    print("=======================================================\n")
    
    engine = RIMEngineV2(
        intuition=VisionIntuitionEngine("robotics", "MOVE_AND_GRASP", "VALIDATE"),
        context_loader=RobotSensorContext(),
        rule_registry=build_robotics_registry()
    )

    print("[SCENARIO 1] LLM sees a coffee mug on the table. Proposes safe coordinates.")
    result1 = engine.process_v2({
        "visual_prompt": "Coffee mug",
        "propose_x": 300.0,
        "propose_y": 200.0,
        "propose_z": 50.0,     # Above the table
        "propose_force_newtons": 15.0
    }, entity_id="ROBOT_ARM_1")

    print("\n[SCENARIO 2] LLM hallucinates! It sees a dropped pen, but miscalculates depth. It commands the arm to go UNDER the table.")
    result2 = engine.process_v2({
        "visual_prompt": "Dropped pen",
        "propose_x": 100.0,
        "propose_y": 100.0,
        "propose_z": -20.0,    # Negative Z! Inside the table!
        "propose_force_newtons": 5.0
    }, entity_id="ROBOT_ARM_1")

    print("\n[SCENARIO 3] LLM sees a heavy battery out of reach.")
    result3 = engine.process_v2({
        "visual_prompt": "Heavy car battery",
        "propose_x": 900.0,    # Outside the 850mm reach
        "propose_y": 0.0,
        "propose_z": 100.0,
        "propose_force_newtons": 100.0 # Will burn out the gripper motor
    }, entity_id="ROBOT_ARM_1")
