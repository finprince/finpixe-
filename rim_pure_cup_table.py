import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from rim_gateway.rim_engine_v2 import RuleRegistry, Rule, RuleType
from rim_gateway.rim_infinite_generator import InfinitePermutationEngine

# 1. System 2 Physics Rule: Gravity and Collision
def build_physics_registry():
    registry = RuleRegistry()
    def check_table_collision(intent, context):
        z_pos = intent.fields["z_position"].value
        if z_pos > 0.0:
            return False, 1.0, "Gravity Violation: Cup is floating.", []
        if z_pos < 0.0:
            return False, 1.0, "Collision Violation: Cup is sinking into the table.", []
        return True, 1.0, "Physics Valid: Cup is resting on the table.", []
    
    registry.register("physics", "PLACE_CUP", Rule("GRAVITY_COLLISION", RuleType.ABSOLUTE, check_table_collision))
    return registry

# 2. The Permutation Seed
seed = {
    "radius": [3.5],
    "height": [7.8],
    "z_position": [5.0, -3.0, 0.0] # Floating, Sinking, Resting
}

# 3. RIM generates and filters the dataset
generator = InfinitePermutationEngine("physics", "PLACE_CUP", build_physics_registry())
result = generator.generate_dataset(seed)

# Ensure we have a valid output
valid_config = result["valid_dataset"][0]
r = valid_config["radius"]
h = valid_config["height"]
z_base = valid_config["z_position"]

# 4. Pure Mathematical Rendering of the RIM Output
theta = np.linspace(0, 2 * np.pi, 100)
z = np.linspace(z_base, z_base + h, 100)
theta_grid, z_grid = np.meshgrid(theta, z)
x_grid = r * np.cos(theta_grid)
y_grid = r * np.sin(theta_grid)

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Plot the Table Surface
table_x, table_y = np.meshgrid(np.linspace(-10, 10, 10), np.linspace(-10, 10, 10))
table_z = np.zeros_like(table_x)
ax.plot_surface(table_x, table_y, table_z, alpha=0.3, color='saddlebrown')

# Plot the Cup Cylinder
ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.7, color='cyan', edgecolor='blue', linewidth=0.2)

ax.set_title("PURE RIM OUTPUT: Cup on a Table\n(Filtered by System 2 Gravity Constraints)", pad=20)
ax.set_xlabel("X Axis")
ax.set_ylabel("Y Axis")
ax.set_zlabel("Z Axis (Height)")
ax.set_zlim(-5, 10)

output_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\pure_rim_cup_on_table.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Image saved to {output_path}")
