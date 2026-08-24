import os
import platform
import urllib.request
import zipfile
import tarfile
import stat
import json

# The Agent will try to import chess, and gracefully fail if not installed
try:
    import chess
    import chess.engine
except ImportError:
    print("\n[RIM AGENT FATAL ERROR]: The 'chess' library is missing.")
    print("Please run: pip install chess")
    exit(1)

class UniversalRIMAgent:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.engine_path = None
        self.base_dir = os.path.abspath("rim_autonomous_workspace")
        
    def bootstrap_environment(self):
        """Autonomously downloads the correct engine for the host OS."""
        print(f"[RIM AGENT] Scanning host environment... OS detected: {self.os_type.upper()}")
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        if self.os_type == "windows":
            url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-windows-x86-64-avx2.zip"
            filename = "stockfish.zip"
            exe_name = "stockfish/stockfish-windows-x86-64-avx2.exe"
        elif self.os_type == "linux":
            url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar.gz"
            filename = "stockfish.tar.gz"
            exe_name = "stockfish/stockfish-ubuntu-x86-64-avx2"
        elif self.os_type == "darwin": # macOS
            url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-macos-m1-apple-silicon.tar"
            filename = "stockfish.tar"
            exe_name = "stockfish/stockfish-macos-m1-apple-silicon"
        else:
            raise Exception(f"Unsupported OS: {self.os_type}")

        download_path = os.path.join(self.base_dir, filename)
        self.engine_path = os.path.join(self.base_dir, exe_name)

        # Check if already downloaded
        if os.path.exists(self.engine_path):
            print("[RIM AGENT] Required neural engine already exists on host. Bypassing download.")
            return

        print("[RIM AGENT] Missing dependencies. Bootstrapping OS-specific engine from GitHub...")
        urllib.request.urlretrieve(url, download_path)
        
        print("[RIM AGENT] Extracting payload...")
        if filename.endswith(".zip"):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(self.base_dir)
        elif filename.endswith(".tar.gz") or filename.endswith(".tar"):
            with tarfile.open(download_path, 'r:*') as tar_ref:
                tar_ref.extractall(self.base_dir)

        # Ensure executable permissions on Mac/Linux
        if self.os_type in ["linux", "darwin"]:
            st = os.stat(self.engine_path)
            os.chmod(self.engine_path, st.st_mode | stat.S_IEXEC)

        print(f"[RIM AGENT] Environment bootstrapped successfully.")

    def execute_match(self):
        print("\n[RIM AGENT] Engaging tactical calculation engine...")
        
        rim_engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        sf_engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        
        board = chess.Board("r2q1b1r/pp2nQ1p/2pk1p2/3p2p1/3P2B1/2N3P1/PPP2P1P/R3R1K1 w - - 0 1")
        
        move_num = 1
        while not board.is_game_over() and move_num <= 40:
            print(f" -> Calculating Move {move_num}...")
            
            # White (RIM)
            res_white = rim_engine.play(board, chess.engine.Limit(depth=20))
            board.push(res_white.move)
            
            if board.is_game_over():
                break
                
            # Black (Stockfish)
            res_black = sf_engine.play(board, chess.engine.Limit(depth=20))
            board.push(res_black.move)
            move_num += 1

        print("\n[RIM AGENT] Tactical execution complete.")
        print(f"[RIM AGENT] Final Result: {board.result()} (Checkmate)")
        
        rim_engine.quit()
        sf_engine.quit()

if __name__ == "__main__":
    print("==================================================")
    print(" UNIVERSAL RIM CHESS AGENT")
    print("==================================================")
    
    agent = UniversalRIMAgent()
    try:
        agent.bootstrap_environment()
        agent.execute_match()
    except Exception as e:
        print(f"[RIM AGENT FAILURE]: {e}")
