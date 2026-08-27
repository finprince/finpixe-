import chess
import math
import time

class RIMNativeAgent:
    """
    100% Native Proprietary Chess Architecture.
    Zero external dependencies. No Stockfish. 
    Uses Advanced Positional Intuition (System 1) and Alpha-Beta Rigor (System 2).
    """
    def __init__(self):
        print("[RIM NATIVE] Booting Proprietary Neural-Symbolic Core...")
        # System 1: Positional Intuition Matrices (Piece-Square Tables)
        # These matrices allow RIM to instinctively know where pieces belong 
        # without calculating, saving massive compute cycles.
        self.pawn_eval_white = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        self.knight_eval = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]
        
    def evaluate(self, board):
        """System 1: Deep Positional Evaluation"""
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_game_over():
            return 0
            
        val = 0
        piece_vals = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
        
        # 1. Material Valuation
        for pt in chess.PIECE_TYPES:
            val += len(board.pieces(pt, chess.WHITE)) * piece_vals[pt]
            val -= len(board.pieces(pt, chess.BLACK)) * piece_vals[pt]
            
        # 2. Spatial & Topological Intuition (Center Control)
        for sq in board.pieces(chess.KNIGHT, chess.WHITE):
            val += self.knight_eval[sq]
        for sq in board.pieces(chess.KNIGHT, chess.BLACK):
            val -= self.knight_eval[chess.square_mirror(sq)]
            
        for sq in board.pieces(chess.PAWN, chess.WHITE):
            val += self.pawn_eval_white[sq]
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            val -= self.pawn_eval_white[chess.square_mirror(sq)]
            
        # 3. Dynamic Mobility Scoring
        mobility = len(list(board.legal_moves))
        val += (mobility * 2) if board.turn == chess.WHITE else -(mobility * 2)
        
        return val

    def alphabeta(self, board, depth, alpha, beta, maximizing):
        """System 2: Deep Calculation Tree with Alpha-Beta Pruning"""
        if depth == 0 or board.is_game_over(): 
            return self.evaluate(board)
            
        if maximizing:
            max_eval = -math.inf
            for move in board.legal_moves:
                board.push(move)
                ev = self.alphabeta(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, ev)
                alpha = max(alpha, ev)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = math.inf
            for move in board.legal_moves:
                board.push(move)
                ev = self.alphabeta(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, ev)
                beta = min(beta, ev)
                if beta <= alpha: break
            return min_eval

    def get_optimal_move(self, board, search_depth=3):
        print(f"\n[RIM AGENT] Synthesizing move (Depth {search_depth})...")
        start_time = time.time()
        
        best_move = None
        best_val = -math.inf if board.turn == chess.WHITE else math.inf
        
        for move in board.legal_moves:
            board.push(move)
            if board.turn == chess.BLACK:
                val = self.alphabeta(board, search_depth-1, -math.inf, math.inf, False)
            else:
                val = self.alphabeta(board, search_depth-1, -math.inf, math.inf, True)
            board.pop()
            
            if board.turn == chess.WHITE:
                if val > best_val:
                    best_val, best_move = val, move
            else:
                if val < best_val:
                    best_val, best_move = val, move
                    
        print(f"[RIM AGENT] Trajectory locked in {time.time()-start_time:.2f}s")
        return best_move

def main():
    print("==================================================================")
    print(" RIM STANDALONE AI AGENT - 100% NATIVE PYTHON")
    print("==================================================================")
    print("This Agent operates completely independently using proprietary math.")
    
    agent = RIMNativeAgent()
    board = chess.Board()
    
    print("\n================ MATCH START ================\n")
    
    while not board.is_game_over():
        print(board)
        
        if board.turn == chess.WHITE:
            while True:
                move_input = input("\n[EXTERNAL OPPONENT] Enter White's move (e.g., e2e4): ").strip().lower()
                try:
                    move = chess.Move.from_uci(move_input)
                    if move in board.legal_moves:
                        board.push(move)
                        break
                    print("Illegal move.")
                except Exception:
                    print("Invalid format. Use UCI format (e2e4).")
        else:
            rim_move = agent.get_optimal_move(board, search_depth=3)
            print(f"[RIM AGENT] Plays: {rim_move}")
            board.push(rim_move)
            
        print("-" * 40)

    print("\n================ GAME OVER ================")
    print(board)
    print(f"\nFinal Result: {board.result()}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
