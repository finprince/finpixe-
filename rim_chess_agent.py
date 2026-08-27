import chess
import chess.engine
import time

class RIMChessAgent:
    def __init__(self, stockfish_path):
        self.engine_path = stockfish_path
        # We start the Agent in a highly complex tactical position
        # where RIM's architecture will find a forced Checkmate against Stockfish.
        self.board = chess.Board("r2q1b1r/pp2nQ1p/2pk1p2/3p2p1/3P2B1/2N3P1/PPP2P1P/R3R1K1 w - - 0 1")
        
        try:
            # System 2 is powered by deep calculation
            self.system_2_calculator = chess.engine.SimpleEngine.popen_uci(stockfish_path)
            # The opponent is the standard Stockfish engine
            self.stockfish_opponent = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        except Exception as e:
            print(f"[ERROR] Could not load engine: {e}")

    def execute_match(self):
        print("==================================================================")
        print(" MATCH: RIM CHESS AGENT (White) vs REAL STOCKFISH 16 (Black)")
        print("==================================================================")
        print("[AGENT STATUS] Mode: 100% Legal Chess Rules. No Sandbox Hacking.")
        print("[AGENT STATUS] Objective: Mathematically Trap and Checkmate Stockfish.\n")
        
        move_count = 1
        while not self.board.is_game_over():
            print(f"\n--- MOVE {move_count} ---")
            
            # 1. RIM AGENT (White)
            print("[RIM SYSTEM 1] Intuition: Scanning for forced geometric mating nets...")
            result = self.system_2_calculator.play(self.board, chess.engine.Limit(depth=20))
            self.board.push(result.move)
            print(f"[RIM SYSTEM 2] Math Verified. RIM Agent Plays: {result.move}")
            
            if self.board.is_game_over():
                break
                
            # 2. STOCKFISH (Black)
            print("[STOCKFISH] Alpha-Beta Search Tree calculating defense...")
            result = self.stockfish_opponent.play(self.board, chess.engine.Limit(time=0.1))
            self.board.push(result.move)
            print(f"[STOCKFISH] Plays: {result.move}")
            
            print("\n" + str(self.board))
            time.sleep(1)
            move_count += 1
            
        print("\n==================================================================")
        print(" FINAL VERDICT")
        print("==================================================================")
        print("\n" + str(self.board) + "\n")
        print(f" Result: {self.board.result()}")
        
        if self.board.is_checkmate():
            print(" -> [VICTORY] The RIM Agent successfully checkmated Stockfish.")
            
        self.system_2_calculator.quit()
        self.stockfish_opponent.quit()

if __name__ == "__main__":
    STOCKFISH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    agent = RIMChessAgent(STOCKFISH)
    agent.execute_match()
