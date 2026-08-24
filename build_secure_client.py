import os
import shutil
import subprocess
import sys

base_dir = r"c:\ast-rim-optimizer"
source_dir = os.path.join(base_dir, "rim_gateway")
client_dir = os.path.join(base_dir, "client")
client_pkg_dir = os.path.join(client_dir, "rim_gateway")

# 1. Fresh Client Directory
if os.path.exists(client_dir):
    shutil.rmtree(client_dir)
os.makedirs(client_pkg_dir)

# 2. Copy the source files
py_files = [f for f in os.listdir(source_dir) if f.endswith('.py')]
for file in py_files:
    shutil.copy(os.path.join(source_dir, file), os.path.join(client_pkg_dir, file))

# 3. Write the Cython setup.py script
setup_code = """
from setuptools import setup
from Cython.Build import cythonize
import os
import glob

# Find all python files except setup.py
py_files = glob.glob('*.py')
if 'setup.py' in py_files:
    py_files.remove('setup.py')

setup(
    name='RIM Gateway Secure',
    ext_modules=cythonize(py_files, compiler_directives={'language_level': "3"}),
    zip_safe=False,
)
"""
setup_path = os.path.join(client_pkg_dir, "setup.py")
with open(setup_path, "w") as f:
    f.write(setup_code)

print(f"Secured client folder created at {client_pkg_dir}")
print("Installing Cython and attempting C++ compilation...")

# 4. Install Cython
subprocess.run([sys.executable, "-m", "pip", "install", "cython", "wheel"], check=True)

# 5. Run the compilation
try:
    result = subprocess.run([sys.executable, "setup.py", "build_ext", "--inplace"], 
                            cwd=client_pkg_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print("\nSUCCESS! Python code was compiled into C-extensions.")
        # Cleanup original .py files and C files to leave ONLY the secure binaries
        for file in os.listdir(client_pkg_dir):
            if file.endswith(".py") and file != "__init__.py": # Keep init so it acts as a package
                os.remove(os.path.join(client_pkg_dir, file))
            elif file.endswith(".c"):
                os.remove(os.path.join(client_pkg_dir, file))
        print("Source code deleted. Only secure binaries remain.")
    else:
        print("\nCOMPILATION FAILED (Likely missing C++ Build Tools):")
        print(result.stderr)
except Exception as e:
    print(f"\nError running compilation: {e}")
