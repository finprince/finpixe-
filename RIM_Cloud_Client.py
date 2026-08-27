import chess
import chess.engine
import urllib.request
import json
import time

def call_aws_rim_agent(fen):
    """Sends the board state to the AWS Cloud Node and gets the AI's move."""
    # When deployed to production, change this IP to the AWS EC2 Public IP
    AWS_NODE_URL = "http://127.0.0.1:8080" 
    
    data = json.dumps({"fen": fen}).encode('utf-8')
    req = urllib.request.Request(AWS_NODE_URL, data=data, headers={'Content-Type': 'application/json'})
    
    print("\n[CLIENT] Pinging AWS Cloud Node for RIM's calculation...")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['best_move'], result['compute_time']
    except Exception as e:
        print(f"[FATAL ERROR] Could not connect to AWS Node: {e}")
        print("Make sure RIM_AWS_Cloud_Node.py is running in another terminal!")
        exit(1)

def main():
    print("==================================================================")
    print(" RIM CLOUD CLIENT - ENTERPRISE EDITION")
    print("==================================================================")
    
    # Path to local Stockfish (representing the legacy system we are fighting)
    STOCKFISH_PATH = r"C:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    
    print("\nSelect Opponent for AWS RIM Agent (Black):")
    print(" 1. Human (You play locally)")
    print(" 2. Local Stockfish 16 (Engine vs Cloud AI)")
    choice = input("Enter choice (1 or 2): ").strip()
    
    sf_engine = None
    if choice == '2':
        sf_engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        print("[CLIENT] Local Stockfish Engine Booted.")

    board = chess.Board()
    print("\n================ MATCH START ================\n")
    
    while not board.is_game_over():
        print(board)
        
        # White's Turn (The Opponent running locally)
        if board.turn == chess.WHITE:
            if choice == '1':
                while True:
                    move_input = input("\n[LOCAL OPPONENT] Enter White's move: ").strip().lower()
                    try:
                        move = chess.Move.from_uci(move_input)
                        if move in board.legal_moves: break
                        print("Illegal move.")
                    except:
                        print("Invalid format.")
            else:
                print("\n[LOCAL STOCKFISH] Calculating...")
                result = sf_engine.play(board, chess.engine.Limit(time=0.1))
                move = result.move
                print(f"[LOCAL STOCKFISH] Plays: {move}")
            board.push(move)
            
        # Black's Turn (AWS RIM Agent)
        else:
            rim_move_uci, compute_time = call_aws_rim_agent(board.fen())
            move = chess.Move.from_uci(rim_move_uci)
            print(f"[AWS RIM AGENT] Cloud response received in {compute_time:.2f}s. Plays: {move}")
            board.push(move)
            
        print("-" * 50)

    print("\n================ MATCH OVER ================")
    print(board)
    print(f"\nFinal Result: {board.result()}")
    
    if sf_engine: sf_engine.quit()

if __name__ == "__main__":
    main()
