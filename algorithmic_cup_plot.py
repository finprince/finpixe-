import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

# 1. The Algorithmic Discovery Engine Output (Pure Math)
radius = 3.5  # cm
height = 7.795  # cm (to hold exactly 300ml)

# 2. Generate the geometry using pure Trigonometry (No LLM/AI)
theta = np.linspace(0, 2 * np.pi, 100)
z = np.linspace(0, height, 100)
theta_grid, z_grid = np.meshgrid(theta, z)

x_grid = radius * np.cos(theta_grid)
y_grid = radius * np.sin(theta_grid)

# Base of the cup
r_base = np.linspace(0, radius, 50)
theta_base, r_base_grid = np.meshgrid(theta, r_base)
x_base = r_base_grid * np.cos(theta_base)
y_base = r_base_grid * np.sin(theta_base)
z_base = np.zeros_like(x_base)

# 3. Plot the mathematical blueprint
fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='3d')

# Plot walls
ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.5, color='cyan', edgecolor='blue', linewidth=0.1)

# Plot base
ax.plot_surface(x_base, y_base, z_base, alpha=0.8, color='cyan', edgecolor='blue', linewidth=0.1)

ax.set_title("PURE ALGORITHMIC CUP\n(Radius: 3.5cm | Height: 7.8cm | Vol: 300ml)", pad=20)
ax.set_xlabel("X (cm)")
ax.set_ylabel("Y (cm)")
ax.set_zlabel("Z Height (cm)")
ax.set_zlim(0, 10)

# Save the image
output_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\pure_algorithmic_cup.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Mathematical image saved to {output_path}")
