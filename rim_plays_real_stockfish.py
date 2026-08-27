import chess
import chess.engine
import random
import time

STOCKFISH_PATH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"

def generalized_ai_move(board):
    """
    Simulates a generalized AI (like an LLM) trying to play chess.
    It understands legal moves and captures, but lacks deep search tree logic.
    """
    legal_moves = list(board.legal_moves)
    # Prefer captures if available (basic heuristic)
    captures = [m for m in legal_moves if board.is_capture(m)]
    if captures:
        return random.choice(captures)
    return random.choice(legal_moves)

def run_live_match():
    print("==================================================================")
    print(" LIVE MATCH: GENERALIZED AI (White) vs REAL STOCKFISH 16.1 (Black)")
    print("==================================================================")
    print(f"Loading official C++ binary: {STOCKFISH_PATH}...")
    
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as e:
        print(f"Failed to start Stockfish: {e}")
        return

    board = chess.Board()
    move_count = 1

    while not board.is_game_over():
        print(f"\n--- MOVE {move_count} ---")
        
        # WHITE: Generalized AI
        white_move = generalized_ai_move(board)
        board.push(white_move)
        print(f"[WHITE] Generalized AI plays: {white_move}")
        
        if board.is_game_over():
            break
            
        # BLACK: Real Stockfish
        print("[BLACK] Stockfish 16.1 calculating (100ms search)...")
        result = engine.play(board, chess.engine.Limit(time=0.1))
        black_move = result.move
        board.push(black_move)
        print(f"[BLACK] Stockfish 16.1 plays: {black_move}")
        
        print("\n" + str(board) + "\n")
        time.sleep(0.5)
        move_count += 1
        
        # Failsafe limit
        if move_count > 30:
            print("Match stopped at Move 30 to prevent terminal overflow.")
            break

    print("==================================================================")
    print(" MATCH COMPLETE")
    print(f" Final Board State:")
    print("\n" + str(board) + "\n")
    print(f" Result: {board.result()}")
    
    if board.is_checkmate():
        print(" REASON: Checkmate.")
        
    print("==================================================================")
    engine.quit()

if __name__ == "__main__":
    run_live_match()
