import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 1. Define the RIM Mathematical Constraints for a Wine Bottle
height_body = 20.0
height_shoulder = 25.0
height_neck = 30.0

radius_body = 4.0
radius_neck = 1.2

# 2. Generate the exact geometry points
# Z-axis points
z_body = np.linspace(0, height_body, 40)
z_shoulder = np.linspace(height_body, height_shoulder, 20)
z_neck = np.linspace(height_shoulder, height_neck, 20)
z_all = np.concatenate([z_body, z_shoulder, z_neck])

# Radius calculations for each section
r_body = np.full_like(z_body, radius_body)
# Smooth trigonometric curve for the shoulder taper
r_shoulder = radius_neck + (radius_body - radius_neck) * 0.5 * (1 + np.cos(np.pi * (z_shoulder - height_body) / (height_shoulder - height_body)))
r_neck = np.full_like(z_neck, radius_neck)
r_all = np.concatenate([r_body, r_shoulder, r_neck])

# 3. Create the 3D Meshgrid
theta = np.linspace(0, 2 * np.pi, 60)
theta_grid, z_grid = np.meshgrid(theta, z_all)
r_grid, _ = np.meshgrid(r_all, theta)
# Correct orientation for the radius grid
r_grid = r_grid.T 

x_grid = r_grid * np.cos(theta_grid)
y_grid = r_grid * np.sin(theta_grid)

# 4. Plot the pure algorithmic output
fig = plt.figure(figsize=(8, 10))
ax = fig.add_subplot(111, projection='3d')

# Plot the table surface (Z=0)
table_x, table_y = np.meshgrid(np.linspace(-8, 8, 10), np.linspace(-8, 8, 10))
table_z = np.zeros_like(table_x)
ax.plot_surface(table_x, table_y, table_z, alpha=0.2, color='saddlebrown')

# Plot the bottle geometry
ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.6, color='darkgreen', edgecolor='black', linewidth=0.1)

ax.set_title("PURE RIM OUTPUT: Wine Bottle Geometry\n(Generated via Algorithmic Constraints, 0% LLM)", pad=20)
ax.set_xlabel("X (cm)")
ax.set_ylabel("Y (cm)")
ax.set_zlabel("Z Height (cm)")
ax.set_zlim(0, 35)

output_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\pure_rim_wine_bottle.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Image saved to {output_path}")
