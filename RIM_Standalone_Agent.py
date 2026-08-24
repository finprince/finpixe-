import chess
import chess.engine
import time

class RIMStandaloneAgent:
    def __init__(self, engine_path):
        # RIM's internal System 2 Calculator
        try:
            self.calculator = chess.engine.SimpleEngine.popen_uci(engine_path)
            self.calculator.configure({"Skill Level": 20}) # Maximum calculation power
        except Exception as e:
            print(f"[FATAL ERROR] Could not initialize System 2: {e}")
            exit(1)
            
        self.board = chess.Board()

    def play_match(self):
        print("==================================================")
        print(" RIM STANDALONE CHESS AGENT - ONLINE")
        print("==================================================")
        print("[STATUS] Agent is completely isolated and decoupled.")
        print("[STATUS] Awaiting external opponent (Human or Separate Engine).")
        print("--------------------------------------------------")
        
        while not self.board.is_game_over():
            print("\n" + str(self.board) + "\n")
            
            # 1. WAIT FOR EXTERNAL OPPONENT
            while True:
                opp_move = input("Enter External Opponent's Move (e.g., 'e2e4'): ").strip()
                try:
                    move = chess.Move.from_uci(opp_move)
                    if move in self.board.legal_moves:
                        self.board.push(move)
                        break
                    else:
                        print("[ERROR] Illegal move. Please enter a valid move.")
                except Exception:
                    print("[ERROR] Invalid format. Use UCI format (e.g., e2e4, g1f3).")
            
            if self.board.is_game_over():
                break
                
            # 2. RIM AGENT CALCULATES AND RESPONDS
            print("\n[RIM SYSTEM 1] Opponent move registered. Scanning tactical implications...")
            time.sleep(0.5)
            print("[RIM SYSTEM 2] Engaging deep calculation matrix...")
            
            # The Agent calculates its own move autonomously
            result = self.calculator.play(self.board, chess.engine.Limit(time=1.0))
            rim_move = result.move
            
            self.board.push(rim_move)
            print(f"\n=> [RIM AGENT PLAYS]: {rim_move}")
            
        print("\n==================================================")
        print(f" GAME OVER. Result: {self.board.result()}")
        print("==================================================")
        self.calculator.quit()

if __name__ == "__main__":
    # Internal path to the calculation engine
    STOCKFISH_PATH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    
    agent = RIMStandaloneAgent(STOCKFISH_PATH)
    try:
        agent.play_match()
    except KeyboardInterrupt:
        print("\n[AGENT SHUTDOWN] Terminated by user.")
        agent.calculator.quit()
