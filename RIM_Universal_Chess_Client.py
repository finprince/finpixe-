import chess
import chess.engine
import time

class RIMAgent:
    """The Core RIM Chess Agent. This is the brain that can face any opponent."""
    def __init__(self, engine_path):
        # We power the RIM Agent's calculation (System 2) using a high-depth engine
        try:
            self.brain = chess.engine.SimpleEngine.popen_uci(engine_path)
        except Exception as e:
            print(f"[ERROR] RIM Agent failed to boot: {e}")
            exit(1)

    def get_move(self, board):
        print("\n[RIM AGENT] Calculating optimal trajectory...")
        result = self.brain.play(board, chess.engine.Limit(time=1.0)) # 1 second deep search
        return result.move

    def shutdown(self):
        self.brain.quit()


def get_human_move(board):
    """Allows a human to type their moves in UCI format (e.g., e2e4)."""
    while True:
        move_input = input("\n[HUMAN] Enter your move (e.g., e2e4): ").strip().lower()
        try:
            move = chess.Move.from_uci(move_input)
            if move in board.legal_moves:
                return move
            else:
                print("Illegal move. Please try again.")
        except ValueError:
            print("Invalid format. Please use UCI format like 'e2e4' or 'g1f3'.")


def main():
    print("==================================================================")
    print(" RIM UNIVERSAL CHESS CLIENT - V1.0")
    print("==================================================================")
    print("Booting RIM Agent...")
    
    # Path to the Stockfish binary used for calculations
    ENGINE_PATH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    rim_agent = RIMAgent(ENGINE_PATH)
    
    print("\nSelect the Opponent for the RIM Agent (Black):")
    print(" 1. Human (You play White)")
    print(" 2. Stockfish 16 (Engine plays White)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    board = chess.Board()
    opponent_engine = None
    
    if choice == '2':
        print("\nBooting Stockfish as the opponent...")
        opponent_engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    elif choice != '1':
        print("Invalid choice. Defaulting to Human.")
        choice = '1'

    print("\n================ MATCH START ================\n")
    
    while not board.is_game_over():
        print(board)
        
        # --- WHITE'S TURN (The Opponent) ---
        if board.turn == chess.WHITE:
            if choice == '1':
                move = get_human_move(board)
            else:
                print("\n[STOCKFISH] Calculating...")
                result = opponent_engine.play(board, chess.engine.Limit(time=0.1))
                move = result.move
                print(f"[STOCKFISH] Plays: {move}")
        
        # --- BLACK'S TURN (The RIM Agent) ---
        else:
            move = rim_agent.get_move(board)
            print(f"[RIM AGENT] Plays: {move}")
            
        board.push(move)
        print("-" * 40)

    print("\n================ MATCH OVER ================")
    print(board)
    print(f"\nFinal Result: {board.result()}")
    
    rim_agent.shutdown()
    if opponent_engine:
        opponent_engine.quit()

if __name__ == "__main__":
    main()
