import math
import random

def calculate_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_cog(frame_w, sensors):
    # Center of Gravity Formula: (Sum of (Weight * Position)) / Total Weight
    total_w = frame_w
    sum_x = 0.0 # Frame is at 0,0
    sum_y = 0.0
    
    for s in sensors:
        total_w += s['weight']
        sum_x += s['weight'] * s['x']
        sum_y += s['weight'] * s['y']
        
    return (sum_x / total_w, sum_y / total_w)

def rim_optimize_drone_layout():
    frame_weight = 500.0
    # Sensors and their weights
    sensor_weights = [120.0, 250.0, 80.0]
    
    print("==================================================")
    print(" RIM SYSTEM 2: ITERATIVE PHYSICS OPTIMIZER")
    print("==================================================\n")
    print("Initializing spatial solver...")
    
    # We use a Monte Carlo / Iterative solver (which an LLM cannot do natively)
    # We will search for a layout where CoG is effectively (0,0) and distance > 5cm
    iterations = 0
    max_iterations = 1000000
    
    best_layout = None
    best_cog_error = float('inf')
    
    while iterations < max_iterations:
        iterations += 1
        
        # RIM proposes coordinates algorithmically (not via language token prediction)
        s1 = {'weight': 120.0, 'x': random.uniform(-10, 10), 'y': random.uniform(-10, 10)}
        s2 = {'weight': 250.0, 'x': random.uniform(-10, 10), 'y': random.uniform(-10, 10)}
        s3 = {'weight': 80.0,  'x': random.uniform(-10, 10), 'y': random.uniform(-10, 10)}
        
        # Rule 1: Check Electromagnetic Interference (Distance > 5cm)
        d12 = calculate_distance((s1['x'], s1['y']), (s2['x'], s2['y']))
        d13 = calculate_distance((s1['x'], s1['y']), (s3['x'], s3['y']))
        d23 = calculate_distance((s2['x'], s2['y']), (s3['x'], s3['y']))
        
        if d12 < 5.0 or d13 < 5.0 or d23 < 5.0:
            continue # Physics Violation, reject immediately
            
        # Rule 2: Calculate Center of Gravity Error
        cog_x, cog_y = calculate_cog(frame_weight, [s1, s2, s3])
        error = abs(cog_x) + abs(cog_y)
        
        # We want the CoG to be virtually 0 (within 0.01 margin of error)
        if error < 0.01:
            best_layout = [s1, s2, s3]
            best_cog_error = error
            break
            
    if best_layout:
        print(f"[SUCCESS] Stable Configuration found after {iterations} mathematical iterations.")
        print("Final Coordinates:")
        print(f"  Sensor A (120g): X={best_layout[0]['x']:.2f}, Y={best_layout[0]['y']:.2f}")
        print(f"  Sensor B (250g): X={best_layout[1]['x']:.2f}, Y={best_layout[1]['y']:.2f}")
        print(f"  Sensor C ( 80g): X={best_layout[2]['x']:.2f}, Y={best_layout[2]['y']:.2f}")
        print("\nVerification Checks:")
        cog_x, cog_y = calculate_cog(frame_weight, best_layout)
        print(f"  -> Final Center of Gravity: (X: {cog_x:.5f}, Y: {cog_y:.5f})")
        print(f"  -> Distance A-B: {calculate_distance((best_layout[0]['x'], best_layout[0]['y']), (best_layout[1]['x'], best_layout[1]['y'])):.2f} cm (PASS)")
    else:
        print("[FAILED] Could not find stable configuration.")

if __name__ == "__main__":
    rim_optimize_drone_layout()
