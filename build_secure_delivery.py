import os
import shutil
import subprocess
import glob
import zipfile

base_dir = r"c:\ast-rim-optimizer"
secure_build_dir = os.path.join(base_dir, "secure_build_temp")
gateway_secure = os.path.join(secure_build_dir, "rim_gateway")

print("1. Preparing secure build environment...")
if os.path.exists(secure_build_dir):
    shutil.rmtree(secure_build_dir)
os.makedirs(gateway_secure)

print("2. Encrypting all source code (including new security modules) with PyArmor...")
py_files = glob.glob(os.path.join(base_dir, 'rim_gateway', '*.py'))
subprocess.run(['pyarmor', 'gen', '-O', gateway_secure] + py_files, check=True)

print("3. Copying packaging metadata...")
shutil.copy(os.path.join(base_dir, "pyproject.toml"), secure_build_dir)
# Ensure README exists
readme_path = os.path.join(base_dir, "README_PACKAGE.md")
if not os.path.exists(readme_path):
    with open(readme_path, "w") as f:
        f.write("# RIM Gateway Secure Enterprise Edition")
shutil.copy(readme_path, secure_build_dir)
open(os.path.join(secure_build_dir, 'MANIFEST.in'), 'w').write('recursive-include rim_gateway *.pyd\nrecursive-include rim_gateway *.so\n')
open(os.path.join(secure_build_dir, 'setup.py'), 'w').write('from setuptools import setup\nsetup(include_package_data=True)\n')

print("4. Compiling the Encrypted Python Wheel (.whl)...")
subprocess.run(["python", "-m", "build", "--wheel"], cwd=secure_build_dir, check=True)

print("5. Zipping the final Highly Secured Client Delivery package...")
whl_file = glob.glob(os.path.join(secure_build_dir, "dist", "*.whl"))[0]
final_zip = os.path.join(base_dir, "RIM_SECURED_Client_Delivery.zip")

docs_dir = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff"

with zipfile.ZipFile(final_zip, 'w') as zf:
    # Add the secure installer
    zf.write(whl_file, os.path.basename(whl_file))
    # Add the demo
    zf.write(os.path.join(base_dir, "rim_security_demo.py"), "rim_security_demo.py")
    # Add Docs
    zf.write(os.path.join(docs_dir, "RIM_Cybersecurity_Integration.md"), "RIM_Cybersecurity_Integration.md")
    zf.write(os.path.join(docs_dir, "RIM_Architecture_v3.md"), "RIM_Architecture_v3.md")
    zf.write(os.path.join(docs_dir, "RIM_Technical_Guide.md"), "RIM_Technical_Guide.md")

print(f"\nSUCCESS: Highly secured package created at {final_zip}")
