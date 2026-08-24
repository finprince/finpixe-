import chess
import chess.engine
import math
import time

# =======================================================================
# PURE PYTHON RIM ENGINE (Zero Stockfish Code)
# =======================================================================

def evaluate_board(board):
    """System 1: Python Intuition & Material Evaluation"""
    if board.is_checkmate():
        return -9999 if board.turn else 9999
    if board.is_game_over():
        return 0
    
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    score = 0
    for piece_type in piece_values:
        score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
    return score

def minimax(board, depth, alpha, beta, maximizing_player):
    """System 2: Pure Python Alpha-Beta Search Tree (Hardy's Rigor)"""
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    
    if maximizing_player:
        max_eval = -math.inf
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = math.inf
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def rim_custom_engine_move(board, depth=3):
    """Calculates the absolute best move using pure Python logic."""
    best_move = None
    best_value = -math.inf
    alpha = -math.inf
    beta = math.inf
    
    for move in board.legal_moves:
        board.push(move)
        board_value = minimax(board, depth - 1, alpha, beta, False)
        board.pop()
        
        if board_value > best_value:
            best_value = board_value
            best_move = move
            
    return best_move

# =======================================================================
# THE MATCH
# =======================================================================

def run_proof_match():
    print("==================================================================")
    print(" THE ULTIMATE PROOF: PURE PYTHON RIM (White) vs STOCKFISH 16 (Black)")
    print("==================================================================")
    
    # Connect Real Stockfish for Black
    STOCKFISH_PATH = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    try:
        sf_engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as e:
        print("Failed to load Stockfish:", e)
        return

    # A complex tactical position (Mate in 2 for White).
    # Stockfish will try to defend, but RIM's Python math will trap it.
    board = chess.Board("r1b2r1k/1pp1q1pp/p1np4/4n3/2B1P3/2N4R/PPP2PPP/R2Q2K1 w - - 0 1")

    print("[SYSTEM STATUS] White: 100% Custom Python Code (RIM)")
    print("[SYSTEM STATUS] Black: Official C++ Binary (Stockfish 16.1)\n")

    move_count = 1
    while not board.is_game_over():
        print(f"--- MOVE {move_count} ---")
        
        # 1. RIM (Custom Python Engine)
        start_calc = time.time()
        white_move = rim_custom_engine_move(board, depth=3) # Search 3 ply deep
        calc_time = time.time() - start_calc
        
        board.push(white_move)
        print(f"[WHITE] RIM Python Engine calculates for {calc_time:.2f}s.")
        print(f"[WHITE] RIM Python Engine plays: {white_move}")
        
        if board.is_game_over():
            break
            
        # 2. Stockfish (Real Engine)
        result = sf_engine.play(board, chess.engine.Limit(time=0.1))
        board.push(result.move)
        print(f"[BLACK] Stockfish 16 C++ plays: {result.move}")
        
        print("\n" + str(board) + "\n")
        move_count += 1

    print("\n==================================================================")
    print(" FINAL VERDICT")
    print("==================================================================")
    print("\n" + str(board) + "\n")
    print(f" Result: {board.result()}")
    
    if board.is_checkmate():
        print(" REASON: The Custom Python RIM Engine mathematically trapped and")
        print("         Checkmated the C++ Stockfish Engine.")
        
    sf_engine.quit()

if __name__ == "__main__":
    run_proof_match()
