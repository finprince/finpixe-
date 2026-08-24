import subprocess
import time
import sys
import os

def main():
    print("[START] Booting up AST-RIM Multi-Language Portal...")
    
    # 1. Start Python FastAPI Backend
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(".")
    
    print("Starting Python Engine (Port 8000)...")
    python_backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "ast_rim.api:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env
    )
    
    # 2. Start Node.js React Engine
    print("Starting Node.js React Engine (Port 8001)...")
    node_dir = os.path.join(os.path.abspath("."), "ast-rim-js")
    node_backend = subprocess.Popen(
        ["node", "server.js"],
        cwd=node_dir,
        shell=True # Shell true needed on windows
    )

    # 3. Start Vite Frontend
    print("Starting Vite Frontend (Port 5050)...")
    frontend_dir = os.path.join(os.path.abspath("."), "ast-rim-portal")
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", "5050"],
        cwd=frontend_dir,
        shell=True # Shell true needed on windows for npm
    )
    
    print("\n[OK] Triple-Server Portal is running!")
    print("-> Frontend UI: http://localhost:5050")
    print("-> Python API: http://localhost:8000")
    print("-> React API: http://localhost:8001\n")
    print("Press Ctrl+C to stop all servers.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down portal...")
        python_backend.terminate()
        node_backend.terminate()
        frontend.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
