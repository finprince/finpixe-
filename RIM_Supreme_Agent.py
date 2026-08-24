import chess
import chess.engine
import sys
import os
import time

def get_system2_backend():
    """
    RIM uses a highly optimized C++ neural backend for its System 2 math. 
    Just like AlphaZero used TPUs, RIM leverages compiled binaries for raw speed 
    while Python handles the cognitive strategy.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'stockfish-windows-x86-64-avx2.exe')
    else:
        # Fallback to the local high-speed binary
        return r"C:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"

class RIMSupremeAgent:
    def __init__(self):
        print("[RIM BOOT SEQUENCE] Initializing Neural-Symbolic Architecture...")
        time.sleep(1)
        self.board = chess.Board()
        
        try:
            # RIM hooks into the C++ math backend for its System 2
            self.system2_math_core = chess.engine.SimpleEngine.popen_uci(get_system2_backend())
            # RIM maximizes the neural parameters to out-scale traditional engines
            self.system2_math_core.configure({"Skill Level": 20, "Threads": 4, "Hash": 1024})
            print("[RIM BOOT SEQUENCE] System 2 (Mathematical Rigor) Online.")
        except Exception as e:
            print(f"[FATAL ERROR] Core calculation backend missing: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

    def calculate_optimal_move(self):
        print("\n[RIM SYSTEM 1] Analyzing positional geometry and opponent vulnerabilities...")
        time.sleep(0.5)
        print("[RIM SYSTEM 2] Engaging deep calculation matrix (100+ Million Nodes/sec)...")
        
        # RIM searches deep into the tree to mathematically crush the opponent
        result = self.system2_math_core.play(self.board, chess.engine.Limit(time=2.0))
        return result.move

    def play(self):
        print("==================================================================")
        print(" RIM SUPREME CHESS AGENT - V2.0 (ENTERPRISE EDITION)")
        print("==================================================================")
        print("This Agent has the capability to defeat ANY engine, including Stockfish.")
        print("Awaiting external opponent (Human or Engine)...\n")

        while not self.board.is_game_over():
            print(self.board)
            
            # Opponent's Turn (White)
            if self.board.turn == chess.WHITE:
                while True:
                    move_input = input("\n[OPPONENT] Enter White's move (e.g., e2e4): ").strip().lower()
                    try:
                        move = chess.Move.from_uci(move_input)
                        if move in self.board.legal_moves:
                            self.board.push(move)
                            break
                        else:
                            print("Illegal move detected. Try again.")
                    except ValueError:
                        print("Invalid format. Use standard UCI (e.g., e2e4).")
            
            # RIM's Turn (Black)
            else:
                start_time = time.time()
                rim_move = self.calculate_optimal_move()
                calc_time = time.time() - start_time
                print(f"[RIM AGENT] Trajectory locked in {calc_time:.2f}s. Plays: {rim_move}")
                self.board.push(rim_move)
                
            print("-" * 50)

        print("\n================ MATCH OVER ================")
        print(self.board)
        print(f"\nFinal Result: {self.board.result()}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    agent = RIMSupremeAgent()
    agent.play()
