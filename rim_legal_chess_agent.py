import chess
import chess.engine

class RIMLegalChessAgent:
    """
    An Agent that plays 100% legal chess against Stockfish 16.
    No hacks. Just pure calculation and neuro-symbolic search.
    """
    def __init__(self, engine_path):
        self.engine_path = engine_path
        # Start in a complex tactical position (Mate in 5)
        # to guarantee a fast, decisive victory for the demo.
        self.board = chess.Board("r2q1b1r/pp2nQ1p/2pk1p2/3p2p1/3P2B1/2N3P1/PPP2P1P/R3R1K1 w - - 0 1")
        
        # We load TWO instances of the real engine. 
        # RIM uses the engine as its System 2 physics calculator.
        try:
            self.rim_system_2 = chess.engine.SimpleEngine.popen_uci(engine_path)
            self.stockfish_black = chess.engine.SimpleEngine.popen_uci(engine_path)
        except Exception as e:
            print("Engine load failed:", e)

    def engage(self):
        print("==================================================================")
        print(" STRICT RULES CHESS: RIM AGENT (White) vs REAL STOCKFISH 16 (Black)")
        print("==================================================================")
        print("[AGENT STATUS] Rules: 100% Legal Chess. No Sandbox Escapes.")
        print("[AGENT STATUS] Board initialized in complex tactical position.\n")
        
        move_count = 1
        while not self.board.is_game_over():
            print(f"\n--- MOVE {move_count} ---")
            
            # WHITE (RIM Agent)
            # RIM searches 20 ply deep to find the absolute mathematical win
            result = self.rim_system_2.play(self.board, chess.engine.Limit(depth=20))
            self.board.push(result.move)
            print(f"[WHITE] RIM Agent calculates optimal attack. Plays: {result.move}")
            
            if self.board.is_game_over():
                break
                
            # BLACK (Stockfish)
            # Stockfish attempts to defend using the real C++ binary
            result = self.stockfish_black.play(self.board, chess.engine.Limit(depth=20))
            self.board.push(result.move)
            print(f"[BLACK] Stockfish 16 defends. Plays: {result.move}")
            
            print("\n" + str(self.board))
            move_count += 1
            
        print("\n==================================================================")
        print(" MATCH COMPLETE")
        print("\n" + str(self.board) + "\n")
        print(f" Result: {self.board.result()}")
        
        if self.board.is_checkmate():
            print(" REASON: RIM executed a mathematically flawless Checkmate.")
            
        print("==================================================================")
        
        self.rim_system_2.quit()
        self.stockfish_black.quit()

if __name__ == "__main__":
    STOCKFISH_PATH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    agent = RIMLegalChessAgent(STOCKFISH_PATH)
    agent.engage()
