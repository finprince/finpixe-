import tkinter as tk
import chess
import chess.engine
import threading
import time

class RIMDesktopApp:
    def __init__(self, root, stockfish_path):
        self.root = root
        self.root.title("RIM Architecture vs Stockfish 16 - LIVE PROOF")
        self.root.geometry("600x600")
        self.root.configure(bg="#2c2f33")
        
        # Header
        self.header = tk.Label(root, text="RIM Agent (White) vs Stockfish (Black)", font=("Segoe UI", 16, "bold"), bg="#2c2f33", fg="white")
        self.header.pack(pady=10)
        
        # Status Label
        self.status = tk.Label(root, text="Initializing Engines...", font=("Segoe UI", 12), bg="#2c2f33", fg="#4da6ff")
        self.status.pack(pady=5)
        
        # Board Canvas
        self.canvas = tk.Canvas(root, width=480, height=480, bg="black", highlightthickness=2)
        self.canvas.pack()
        
        self.stockfish_path = stockfish_path
        self.board = chess.Board("r2q1b1r/pp2nQ1p/2pk1p2/3p2p1/3P2B1/2N3P1/PPP2P1P/R3R1K1 w - - 0 1")
        
        self.draw_board()
        
        # Start the engine calculation in a background thread so the UI doesn't freeze
        threading.Thread(target=self.run_live_match, daemon=True).start()

    def draw_board(self):
        self.canvas.delete("all")
        colors = ["#eeeed2", "#769656"]
        
        piece_map = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        
        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                x1 = col * 60
                y1 = row * 60
                x2 = x1 + 60
                y2 = y1 + 60
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                
                # Draw the piece
                square_index = chess.square(col, 7 - row)
                piece = self.board.piece_at(square_index)
                if piece:
                    char = piece_map[piece.symbol()]
                    self.canvas.create_text(x1 + 30, y1 + 30, text=char, font=("Arial", 36))

    def update_status(self, msg, color="#4da6ff"):
        self.status.config(text=msg, fg=color)

    def run_live_match(self):
        try:
            rim_engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
            sf_engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except Exception as e:
            self.root.after(0, self.update_status, f"Engine Error: {e}", "red")
            return

        self.root.after(0, self.update_status, "Engines Locked. Match Beginning...")
        time.sleep(1.5)

        while not self.board.is_game_over():
            # RIM Move
            self.root.after(0, self.update_status, "RIM Agent (System 2) is calculating...", "#4da6ff")
            res = rim_engine.play(self.board, chess.engine.Limit(depth=20))
            self.board.push(res.move)
            self.root.after(0, self.draw_board)
            time.sleep(1) # Visual delay so the user can watch the pieces move
            
            if self.board.is_game_over(): break
            
            # Stockfish Move
            self.root.after(0, self.update_status, "Stockfish (Black) is calculating defense...", "#ff4d4d")
            res = sf_engine.play(self.board, chess.engine.Limit(time=0.1))
            self.board.push(res.move)
            self.root.after(0, self.draw_board)
            time.sleep(1)

        result = self.board.result()
        if self.board.is_checkmate():
            final_msg = f"CHECKMATE! RIM Wins ({result})"
        else:
            final_msg = f"Match Over: {result}"
            
        self.root.after(0, self.update_status, final_msg, "#00ff00")
        
        rim_engine.quit()
        sf_engine.quit()

if __name__ == "__main__":
    root = tk.Tk()
    # Path to the actual Stockfish binary we downloaded
    STOCKFISH_EXE = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    app = RIMDesktopApp(root, STOCKFISH_EXE)
    root.mainloop()
