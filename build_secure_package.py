import py_compile
import os

print("Compiling RIM Enterprise Installer to secure bytecode...")
py_compile.compile('rim_enterprise_installer.py', cfile='RIM_Customer_Trial/rim_core_engine.pyc')
print("Compilation successful! Source code hidden.")
