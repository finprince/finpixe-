import os
import sys
import subprocess
import sqlite3
import time

def clear_database():
    db_path = os.path.join("ast_rim", "rim_metrics.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    print("[1/4] Cleared previous analytics database.")

def setup_legacy_code():
    os.makedirs("legacy_client_project", exist_ok=True)
    file1 = """import pandas as custom_pd
def load_data():
    df1 = custom_pd.DataFrame({'sales': [100]})
    df2 = custom_pd.DataFrame({'sales': [200]})
    # Legacy Pandas 1.x syntax using custom alias
    master_df = df1.append(df2)
    deviation = master_df.mad()
    return master_df, deviation
"""
    with open("legacy_client_project/complex_sales.py", "w") as f: f.write(file1)
    print("[2/4] Generated mock legacy client repository.")

def run_cli_migration():
    print("[3/4] Running Enterprise CLI Migration (LibCST + Analytics)...")
    time.sleep(1)
    subprocess.run([sys.executable, "ast_rim/cli.py", "migrate", "legacy_client_project"])

def run_dashboard_generation():
    print("\n[4/4] Generating B2B SaaS Dashboard...")
    time.sleep(1)
    subprocess.run([sys.executable, "ast_rim/cli.py", "dashboard"])

if __name__ == "__main__":
    print("==================================================")
    print("   RIM MIGRATION ENGINE: END-TO-END DEMO          ")
    print("==================================================\n")
    
    clear_database()
    setup_legacy_code()
    run_cli_migration()
    run_dashboard_generation()
    
    print("\n==================================================")
    print("   END-TO-END DEMO COMPLETE                       ")
    print("==================================================")
    print("Open 'b2b_dashboard.html' to view the final results.")
