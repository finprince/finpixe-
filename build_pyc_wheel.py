import os
import shutil
import subprocess
import glob

print("Starting Option 2: Bytecode Compilation Build...")

# 1. Create a clean build directory
build_dir = "build_pyc_dist"
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)
os.makedirs(build_dir)

# 2. Copy the package contents over
shutil.copytree("ast_rim", os.path.join(build_dir, "ast_rim"))

# 3. Compile all .py files to .pyc files directly in the directory (-b flag)
print("Compiling Python files to bytecode...")
subprocess.run(["python", "-m", "compileall", "-b", os.path.join(build_dir, "ast_rim")])

# 4. Delete the raw .py files so they are not packaged!
print("Deleting raw .py source files...")
for py_file in glob.glob(os.path.join(build_dir, "ast_rim", "*.py")):
    os.remove(py_file)

# 5. Write a custom setup.py in the build directory
setup_script = """
from setuptools import setup, find_packages

setup(
    name="rim-migration-engine",
    version="1.0.0",
    description="RIM: Automated AST Legacy Migration Engine",
    author="RIM Enterprise",
    packages=["ast_rim"],
    # Tell setuptools to include the .pyc files since there are no .py files left
    package_data={"ast_rim": ["*.pyc"]},
    include_package_data=True,
    install_requires=[],
)
"""
with open(os.path.join(build_dir, "setup.py"), "w") as f:
    f.write(setup_script)

# 6. Build the wheel
print("Building the final wheel...")
subprocess.run(["python", "setup.py", "bdist_wheel"], cwd=build_dir)

print("\nBuild Complete!")
print(f"Your bytecode wheel is located at: {os.path.abspath(os.path.join(build_dir, 'dist'))}")
