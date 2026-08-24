import cv2
import numpy as np
import os
import random

def generate_synthetic_dirt(base_img_path=None, output_path="synthetic_dirty.jpg"):
    # 1. Load base image or create a blank white tile
    if base_img_path and os.path.exists(base_img_path):
        img = cv2.imread(base_img_path)
    else:
        print("No base image provided. Creating a clean white tile (800x800)...")
        img = np.ones((800, 800, 3), dtype=np.uint8) * 255
        
    h, w, _ = img.shape
    
    # 2. Add Grime Layer (Gaussian Noise to simulate film/dust)
    print("Applying procedural grime layer...")
    # Create random noise
    noise = np.random.randint(0, 50, (h, w, 3), dtype=np.uint8)
    # Blend the noise onto the original image (darkens it randomly)
    dirty_img = cv2.subtract(img, noise)
    
    # 3. Add Water Stains (Semi-transparent brown/grey circles)
    print("Applying water stains and soap scum...")
    num_stains = random.randint(10, 30)
    for _ in range(num_stains):
        cx = random.randint(0, w)
        cy = random.randint(0, h)
        radius = random.randint(20, 80)
        # Dirty brown/grey color (BGR format)
        color = (random.randint(50, 100), random.randint(80, 120), random.randint(100, 150))
        opacity = random.uniform(0.1, 0.4)
        
        overlay = dirty_img.copy()
        cv2.circle(overlay, (cx, cy), radius, color, -1)
        # Blur the stain to make it look like dried water
        cv2.GaussianBlur(overlay, (21, 21), 0, overlay)
        cv2.addWeighted(overlay, opacity, dirty_img, 1 - opacity, 0, dirty_img)
        
    # 4. Add Heavy Dirt Speckles (Hair, mud, solid particles)
    print("Applying physical dirt speckles...")
    num_speckles = random.randint(500, 2000)
    for _ in range(num_speckles):
        cx = random.randint(0, w-1)
        cy = random.randint(0, h-1)
        # Draw a tiny black/brown speck
        dirty_img[cy, cx] = [0, random.randint(0,50), random.randint(0,50)]
        if random.random() > 0.5:
            # Make some speckles slightly larger (2x2 pixels)
            dirty_img[cy-1:cy+1, cx-1:cx+1] = [0, 0, 0]
            
    # 5. Save the output
    cv2.imwrite(output_path, dirty_img)
    print(f"\n[SUCCESS] Synthetic training image saved to: {os.path.abspath(output_path)}")
    print(f"Dataset Size: 1 images. (Wrap in a loop to generate 10,000+)")

if __name__ == "__main__":
    # Create dataset folder
    dataset_dir = "synthetic_restroom_dataset"
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Generate one sample image to prove the pipeline works
    output_file = os.path.join(dataset_dir, "training_sample_001.jpg")
    generate_synthetic_dirt(output_path=output_file)
