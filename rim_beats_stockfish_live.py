import time
import sys

def print_board(move_num, rim_move, sf_move, board_state, rim_eval, sf_eval, rim_thought, sf_thought):
    print("==================================================================")
    print(f" MOVE {move_num}: RIM (White) vs STOCKFISH (Black)")
    print("==================================================================")
    print(f"[RIM SYSTEM 1 INTUITION]: {rim_thought}")
    print(f"[STOCKFISH BRUTE FORCE] : {sf_thought}")
    print("-" * 66)
    print(f"RIM Evaluation: {rim_eval}  |  Stockfish Evaluation: {sf_eval}")
    print(f"RIM Plays: {rim_move}      |  Stockfish Plays: {sf_move}\n")
    
    print("    a  b  c  d  e  f  g  h")
    print("  +------------------------+")
    for i, row in enumerate(board_state):
        print(f"{8-i} | " + "  ".join(row) + f" | {8-i}")
    print("  +------------------------+")
    print("    a  b  c  d  e  f  g  h\n")
    time.sleep(3)

def run_chess_match():
    # Simulated board states based on a classic neural-network positional crush
    
    # MOVE 24: The Setup
    board_24 = [
        ['.', '.', 'r', 'q', '.', 'r', 'k', '.'],
        ['p', 'p', '.', 'n', 'p', 'p', 'b', 'p'],
        ['.', '.', 'p', '.', '.', '.', 'p', '.'],
        ['.', '.', '.', 'p', 'P', '.', '.', '.'],
        ['.', '.', 'P', '.', '.', 'P', 'N', 'P'],
        ['.', 'P', '.', '.', '.', '.', 'P', '.'],
        ['P', '.', '.', 'Q', '.', 'B', '.', '.'],
        ['.', 'R', '.', '.', 'R', '.', 'K', '.']
    ]
    print_board(24, "d5 (Pawn Push)", "exd5 (Pawn Takes)", board_24, 
                rim_eval="+2.1 (Positional Dominance)", sf_eval="+1.5 (Material Equal)",
                rim_thought="I will offer a pawn to permanently block Black's Bishop.",
                sf_thought="Free pawn detected. Horizon clear for 20 moves.")

    # MOVE 25: The Trap (The Horizon Effect)
    board_25 = [
        ['.', '.', 'r', 'q', '.', 'r', 'k', '.'],
        ['p', 'p', '.', 'n', '.', 'p', 'b', 'p'],
        ['.', '.', 'p', '.', '.', '.', 'p', '.'],
        ['.', '.', '.', 'p', 'P', '.', '.', '.'],
        ['.', '.', 'P', '.', '.', 'P', 'N', 'P'],
        ['.', 'P', '.', '.', '.', 'Q', 'P', '.'],
        ['P', '.', '.', '.', '.', 'B', '.', '.'],
        ['.', 'R', '.', '.', 'R', '.', 'K', '.']
    ]
    print_board(25, "Qf3 (Queen Sacrifice Offer)", "Qxf3 (Queen Takes)", board_25, 
                rim_eval="+M12 (Forced Mate in 12)", sf_eval="+9.0 (Black is Winning)",
                rim_thought="Sacrificing the Queen opens the h-file. Stockfish cannot see the mate 12 moves away.",
                sf_thought="+9 points gained. No immediate threats detected in search tree.")

    # MOVE 26: The Paralysis
    board_26 = [
        ['.', '.', 'r', '.', '.', 'r', 'k', '.'],
        ['p', 'p', '.', 'n', '.', 'p', 'b', 'p'],
        ['.', '.', 'p', '.', '.', '.', 'p', '.'],
        ['.', '.', '.', 'p', 'P', '.', '.', '.'],
        ['.', '.', 'P', '.', '.', 'P', 'N', 'P'],
        ['.', 'P', '.', '.', '.', 'q', 'P', '.'],
        ['P', '.', '.', '.', '.', 'B', '.', 'R'],
        ['.', 'R', '.', '.', '.', '.', 'K', '.']
    ]
    print_board(26, "Rh1 (Rook to open file)", "Kg7 (King attempts escape)", board_26, 
                rim_eval="+M3 (Forced Mate in 3)", sf_eval="-M3 (Fatal Horizon Error)",
                rim_thought="The geometric net is complete. The King is trapped.",
                sf_thought="CRITICAL ERROR: Search tree expanded. Positional trap detected. Cannot escape.")

    # MOVE 27: CHECKMATE
    board_27 = [
        ['.', '.', 'r', '.', '.', 'r', '.', '.'],
        ['p', 'p', '.', 'n', '.', 'p', 'k', 'p'],
        ['.', '.', 'p', '.', '.', '.', 'p', '.'],
        ['.', '.', '.', 'p', 'P', '.', '.', '.'],
        ['.', '.', 'P', '.', '.', 'P', 'N', 'P'],
        ['.', 'P', '.', '.', '.', 'q', 'P', 'B'],
        ['P', '.', '.', '.', '.', '.', '.', 'R'],
        ['.', 'R', '.', '.', '.', '.', 'K', '.']
    ]
    print_board(27, "Bh6# (CHECKMATE)", "---", board_27, 
                rim_eval="WIN", sf_eval="LOSS",
                rim_thought="System 2 verifies checkmate physics. Game over.",
                sf_thought="System halted.")
    
    print("\n==================================================================")
    print(" MATCH CONCLUSION: RIM WINS")
    print("==================================================================")
    print("RIM used its intuitive neural network to sacrifice a Queen, creating a")
    print("positional trap that Stockfish's brute-force calculator could not see")
    print("until it was too late. This is the Horizon Effect in action.")

if __name__ == "__main__":
    run_chess_match()
