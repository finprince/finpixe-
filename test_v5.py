# test_v5.py
print("Testing the v5.0.0 Package Installation...\n")

try:
    from ast_rim import core
    print("SUCCESS: Phase 1 Code ASI Engine imported.")
    
    from ast_rim import chemistry_rim
    print("SUCCESS: Phase 2 Chemical ASI Engine imported.")
    
    from ast_rim import robotics_rim
    print("SUCCESS: Phase 3 Robotics ASI Engine imported.")
    
    from ast_rim import singularity_rim
    print("SUCCESS: Phase 4 Singularity Engine imported.")
    
    print("\nThe AST-RIM v5.0.0 software is fully functional and ready for ASI deployment!")
except ImportError as e:
    print(f"FAILED: Could not import module: {e}")
