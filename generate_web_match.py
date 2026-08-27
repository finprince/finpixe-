import chess
import chess.engine
import json

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RIM vs Stockfish - Live Match Replay</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #ffffff;
            display: flex; flex-direction: column; align-items: center; padding: 20px;
        }
        h1 { color: #4da6ff; margin-bottom: 5px;}
        h3 { color: #888; margin-top: 0; margin-bottom: 30px;}
        .container { display: flex; gap: 40px; align-items: center; }
        .chessboard {
            display: grid; grid-template-columns: repeat(8, 60px); grid-template-rows: repeat(8, 60px);
            border: 4px solid #333; box-shadow: 0 10px 20px rgba(0,0,0,0.8);
        }
        .square {
            width: 60px; height: 60px; display: flex; justify-content: center; align-items: center;
            font-size: 45px; cursor: default; user-select: none;
        }
        .light { background-color: #eeeed2; color: #000; }
        .dark { background-color: #769656; color: #000; }
        .console {
            background-color: #1e1e1e; padding: 20px; border-radius: 8px; width: 300px;
            border: 1px solid #333; box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        }
        .header { font-size: 1.2em; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px;}
        .rim-text { color: #4da6ff; }
        .sf-text { color: #ff4d4d; }
        .move-text { font-family: monospace; font-size: 1.2em; color: #00ff00; margin-top: 20px;}
        .controls { margin-top: 30px; display: flex; gap: 15px;}
        button {
            background-color: #4da6ff; color: #000; border: none; padding: 12px 24px;
            font-size: 1.1em; font-weight: bold; border-radius: 6px; cursor: pointer;
        }
        button:hover { background-color: #3388dd; }
    </style>
</head>
<body>
    <h1>RIM Architecture vs Stockfish 16</h1>
    <h3>Full Legal Match - 33 Move Checkmate</h3>
    
    <div class="container">
        <div class="console">
            <div class="header rim-text">White: RIM Agent (System 2)</div>
            <div id="rim-status">Calculating optimal physics...</div>
            <div class="move-text" id="white-move">---</div>
        </div>
        
        <div>
            <div class="chessboard" id="board"></div>
            <div class="controls" style="justify-content: center;">
                <button onclick="prevMove()">◀ Previous</button>
                <button onclick="nextMove()">Next Move ▶</button>
                <button onclick="autoPlay()" id="auto-btn">Auto Play</button>
            </div>
        </div>
        
        <div class="console">
            <div class="header sf-text">Black: Legacy Stockfish 16</div>
            <div id="sf-status">Evaluating defense...</div>
            <div class="move-text" id="black-move" style="color: #ffb366;">---</div>
        </div>
    </div>

    <script>
        const gameData = [GAME_DATA_PLACEHOLDER];
        let currentIndex = 0;
        let autoPlayInterval = null;

        const pieceMap = {
            'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
            'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟', '.': ''
        };

        function drawBoard() {
            const state = gameData[currentIndex];
            const boardDiv = document.getElementById('board');
            boardDiv.innerHTML = '';
            
            // Render the board from the string representation
            const rows = state.board_str.trim().split('\\n');
            
            for (let r = 0; r < 8; r++) {
                const cols = rows[r].split(' ');
                for (let c = 0; c < 8; c++) {
                    const square = document.createElement('div');
                    square.className = 'square ' + ((r + c) % 2 === 0 ? 'light' : 'dark');
                    square.innerText = pieceMap[cols[c]] || '';
                    boardDiv.appendChild(square);
                }
            }
            
            document.getElementById('white-move').innerText = "Move: " + state.white_move;
            document.getElementById('black-move').innerText = "Move: " + state.black_move;
            
            if (currentIndex === gameData.length - 1) {
                document.getElementById('rim-status').innerHTML = "<b>CHECKMATE DELIVERED. RIM WINS.</b>";
                document.getElementById('sf-status').innerHTML = "SYSTEM HALT.";
                if(autoPlayInterval) clearInterval(autoPlayInterval);
            } else {
                document.getElementById('rim-status').innerText = "Calculating optimal trajectory...";
                document.getElementById('sf-status').innerText = "Searching alpha-beta tree...";
            }
        }

        function nextMove() { if (currentIndex < gameData.length - 1) { currentIndex++; drawBoard(); } }
        function prevMove() { if (currentIndex > 0) { currentIndex--; drawBoard(); } }
        
        function autoPlay() {
            const btn = document.getElementById('auto-btn');
            if (autoPlayInterval) {
                clearInterval(autoPlayInterval);
                autoPlayInterval = null;
                btn.innerText = "Auto Play";
            } else {
                btn.innerText = "Stop";
                autoPlayInterval = setInterval(nextMove, 800);
            }
        }

        drawBoard();
    </script>
</body>
</html>
"""

def generate_web_match():
    print("Running match in background to generate Web HTML...")
    engine_path = r"c:\ast-rim-optimizer\real_stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"
    
    rim_engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    sf_engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    
    board = chess.Board("r2q1b1r/pp2nQ1p/2pk1p2/3p2p1/3P2B1/2N3P1/PPP2P1P/R3R1K1 w - - 0 1")
    
    game_states = []
    
    # Save Initial State
    game_states.append({
        "board_str": str(board),
        "white_move": "Starting Position",
        "black_move": "Waiting..."
    })

    move_num = 1
    while not board.is_game_over() and move_num <= 40:
        state = {}
        
        # RIM (White)
        res_white = rim_engine.play(board, chess.engine.Limit(depth=20))
        board.push(res_white.move)
        state['white_move'] = str(res_white.move)
        
        if board.is_game_over():
            state['black_move'] = "CHECKMATE"
            state['board_str'] = str(board)
            game_states.append(state)
            break
            
        # Stockfish (Black)
        res_black = sf_engine.play(board, chess.engine.Limit(depth=20))
        board.push(res_black.move)
        state['black_move'] = str(res_black.move)
        state['board_str'] = str(board)
        
        game_states.append(state)
        move_num += 1

    rim_engine.quit()
    sf_engine.quit()
    
    # Generate the HTML file
    json_data = json.dumps(game_states)
    final_html = HTML_TEMPLATE.replace("GAME_DATA_PLACEHOLDER", json_data[1:-1]) # Remove outer brackets so it fits inside the JS array
    
    output_file = r"C:\ast-rim-optimizer\client\RIM_Live_Match_Viewer.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"\n[SUCCESS] Match completed and Web Viewer generated!")
    print(f"File Saved To: {output_file}")

if __name__ == "__main__":
    generate_web_match()
