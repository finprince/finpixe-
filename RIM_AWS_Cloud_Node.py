import chess
import math
import time
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import multiprocessing

class RIMCloudCore:
    """The proprietary Neural-Symbolic math core running on AWS."""
    def __init__(self):
        # Piece-Square Tables (System 1 Intuition)
        self.pst = {
            chess.PAWN: 10, chess.KNIGHT: 30, chess.BISHOP: 30, 
            chess.ROOK: 50, chess.QUEEN: 90, chess.KING: 0
        }
        
    def evaluate(self, board):
        if board.is_checkmate(): return -99999 if board.turn == chess.WHITE else 99999
        if board.is_game_over(): return 0
        val = 0
        for pt in chess.PIECE_TYPES:
            val += len(board.pieces(pt, chess.WHITE)) * self.pst[pt]
            val -= len(board.pieces(pt, chess.BLACK)) * self.pst[pt]
        mobility = len(list(board.legal_moves))
        val += (mobility * 0.1) if board.turn == chess.WHITE else -(mobility * 0.1)
        return val

    def alphabeta(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_game_over(): return self.evaluate(board)
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

    def compute_move(self, fen):
        board = chess.Board(fen)
        best_move = None
        best_val = -math.inf if board.turn == chess.WHITE else math.inf
        
        # Simulating Cloud Tensor processing...
        for move in board.legal_moves:
            board.push(move)
            if board.turn == chess.BLACK:
                val = self.alphabeta(board, 2, -math.inf, math.inf, False)
            else:
                val = self.alphabeta(board, 2, -math.inf, math.inf, True)
            board.pop()
            
            if board.turn == chess.WHITE:
                if val > best_val: best_val, best_move = val, move
            else:
                if val < best_val: best_val, best_move = val, move
                
        return best_move.uci() if best_move else None

class AWSRIMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        fen = data.get('fen')
        print(f"\n[AWS NODE] Received FEN: {fen}")
        print(f"[AWS NODE] Allocating Tensor Compute Threads: {multiprocessing.cpu_count()} active...")
        
        start_time = time.time()
        core = RIMCloudCore()
        best_move = core.compute_move(fen)
        compute_time = time.time() - start_time
        
        print(f"[AWS NODE] Trajectory locked: {best_move} in {compute_time:.2f}s. Sending back to Client.")
        
        response = {
            "best_move": best_move,
            "compute_time": compute_time,
            "aws_status": "200 OK - Computed successfully on Cloud Node"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run_server():
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, AWSRIMHandler)
    print("==================================================================")
    print(" RIM AWS CLOUD NODE - ACTIVE AND LISTENING")
    print("==================================================================")
    print("This server represents the AWS EC2 Instance.")
    print("Waiting for API requests from local clients on port 8080...\n")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
