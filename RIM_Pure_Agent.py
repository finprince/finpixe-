import chess
import math
import time
import sys

class RIMPureAgent:
    """
    100% Proprietary Python Chess Agent. 
    Zero external engine dependencies. No Stockfish.
    """
    def __init__(self):
        print("[RIM SYSTEM] Booting Proprietary Neural-Symbolic Core...")
        
    def evaluate(self, board):
        """System 1: Material and Spatial Evaluation"""
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_game_over():
            return 0
            
        val = 0
        piece_vals = {chess.PAWN: 10, chess.KNIGHT: 30, chess.BISHOP: 30, chess.ROOK: 50, chess.QUEEN: 90, chess.KING: 0}
        
        for pt in chess.PIECE_TYPES:
            val += len(board.pieces(pt, chess.WHITE)) * piece_vals[pt]
            val -= len(board.pieces(pt, chess.BLACK)) * piece_vals[pt]
            
        # Spatial Mobility
        mobility = len(list(board.legal_moves))
        val += (mobility * 0.1) if board.turn == chess.WHITE else -(mobility * 0.1)
        return val

    def alphabeta(self, board, depth, alpha, beta, maximizing):
        """System 2: Deep Calculation Tree"""
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

    def get_move(self, board, depth=3):
        print("\n[RIM AGENT] Synthesizing move...")
        start_time = time.time()
        
        best_move = None
        best_val = -math.inf if board.turn == chess.WHITE else math.inf
        
        for move in board.legal_moves:
            board.push(move)
            if board.turn == chess.BLACK: # After push, evaluating the opponent's turn
                val = self.alphabeta(board, depth-1, -math.inf, math.inf, False)
            else:
                val = self.alphabeta(board, depth-1, -math.inf, math.inf, True)
            board.pop()
            
            if board.turn == chess.WHITE:
                if val > best_val:
                    best_val, best_move = val, move
            else:
                if val < best_val:
                    best_val, best_move = val, move
                    
        print(f"[RIM AGENT] Calculation complete in {time.time()-start_time:.2f}s")
        return best_move


def main():
    print("==================================================================")
    print(" RIM STANDALONE AI AGENT - PURE PYTHON CORE")
    print("==================================================================")
    print("This Agent operates completely independently.")
    print("You can play against it as a Human, or you can run Stockfish")
    print("in a separate window and feed its moves here to test the Agent.")
    
    agent = RIMPureAgent()
    board = chess.Board()
    
    # Let RIM Play Black by default
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
            rim_move = agent.get_move(board, depth=3)
            print(f"[RIM AGENT] Plays: {rim_move}")
            board.push(rim_move)
            
        print("-" * 40)

    print("\n================ GAME OVER ================")
    print(board)
    print(f"\nFinal Result: {board.result()}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
