import os

target = "IMG_20260406_0003.pdf"
found = []
for root, dirs, files in os.walk("."):
    for file in files:
        if target in file or "IMG_20260406_0003" in file:
            found.append(os.path.join(root, file))

print("Found files:")
for f in found:
    print(f)
