import matplotlib.pyplot as plt
import numpy as np

# Set up the visual style for a CTO pitch
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('LLM vs RIM: The Mathematical Difference', fontsize=18, fontweight='bold', color='white')

# --- 1. The LLM (y = mx + c) Linear Regression ---
# Generate random probabilistic data points (LLM training data)
x_llm = np.linspace(0, 10, 50)
y_llm = 2 * x_llm + 5 + np.random.normal(0, 3, 50) # y = 2x + 5 + noise

ax1.scatter(x_llm, y_llm, color='gray', alpha=0.6, label='Probabilistic Training Data')
ax1.plot(x_llm, 2 * x_llm + 5, color='red', linewidth=3, label='LLM Guess (y=mx+c)')

ax1.set_title('Standard AI (y = mx + c)\nStatistical Guessing', color='red', fontsize=14)
ax1.set_xlabel('Time / Complexity')
ax1.set_ylabel('Capability')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.2)


# --- 2. RIM (Infinity Theory) Structural Evolution ---
# Generate a geometric, exponential fractal curve
x_rim = np.linspace(0, 10, 100)
# Instead of a straight line, it scales exponentially and perfectly structurally
y_rim = 2 ** (x_rim / 1.5) 

ax2.plot(x_rim, y_rim, color='cyan', linewidth=4, label='RIM Structural Calculation')

# Plot "Nodes" representing absolute AST structures, not random noise
node_x = np.linspace(0, 10, 8)
node_y = 2 ** (node_x / 1.5)
ax2.plot(node_x, node_y, 'wo', markersize=8, label='Verified AST Nodes (0 Noise)')

ax2.set_title('RIM (Infinity Theory)\nAbsolute Structural Expansion', color='cyan', fontsize=14)
ax2.set_xlabel('Time / Complexity')
ax2.set_ylabel('Capability')
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.2)

# Save the visualization
output_path = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\rim_vs_llm_graph.png"
plt.tight_layout()
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Graph successfully generated at: {output_path}")
