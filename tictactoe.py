# follow.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *
import net_comms


def send_invite(sock:socket, target_user_id:str, app_state: AppState, game_id, symbol):
    # construct tictactoe invite message
    # send to target_ip via unicast UDP
    try:   
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()
        
        message = {
            "TYPE": "TICTACTOE_INVITE",
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "GAMEID": game_id,
            "MESSAGE_ID": str(uuid.uuid4()),     
            "SYMBOL": symbol,   
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|game'
        }

        # Store local game state
        with app_state.lock:
            app_state.active_games[game_id] = {
                "opponent": target_user_id,
                "symbol": symbol,
                "board": [None] * 9,
                "turn": 0,
                "my_turn": True,
                "status": "WAITING"
            }

        net_comms.send_with_ack(sock, message, app_state, target_user["ip"])
        print(f'\n[TICTACTOE] You invited {target_user["display_name"]} to play Tic Tac Toe (Game ID: {game_id})\n')
    except KeyError as e:
        print(f'\n[ERROR] invalid user_id | {e}', end='\n\n')

# Function to handle received invites
def handle_invite(msg, app_state, sock, sender_ip):
    game_id = msg["GAMEID"]
    sender = msg["FROM"]
    symbol = "O" if msg["SYMBOL"] == "X" else "X"

    with app_state.lock:
        # Ignore repeated invites
        if game_id in app_state.active_games:
            print("balls")
            return  
        
        # Store active game
        app_state.active_games[game_id] = {
            "opponent": sender,
            "symbol": symbol,
            "board": [None] * 9,
            "turn": 0,
            "my_turn": False,
            "status": "IN_PROGRESS"
        }

    print("Ballsy")
    net_comms.send_ack(sock, msg["MESSAGE_ID"], sender_ip)
    print(f"\n[INVITE] {sender} invited you to play Tic Tac Toe (Game ID: {game_id})")

# Function to send move to other user
def move(sock: socket, target_user_id: str, app_state: AppState, game_id, position):
    try:   
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()
        message_id = uuid.uuid4()

        with app_state.lock:
            # Get active game
            game = app_state.active_games.get(game_id)
            if not game:
                print(f'[ERROR] Game ID {game_id} not found.')
                return

            if not game["my_turn"]:
                print("[INFO] Not your turn.")
                return

            symbol = game["symbol"]
            board = game["board"]

            if board[position] is not None:
                print("[ERROR] Position already taken.")
                return

            # Apply move
            board[position] = symbol
            game["turn"] += 1
            game["my_turn"] = False

        message = {
            "TYPE": "TICTACTOE_MOVE",
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "GAMEID": game_id,
            "MESSAGE_ID": str(message_id),     
            "POSITION": position,
            "SYMBOL": symbol,
            "TURN": game["turn"],
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|game'
        }

        net_comms.send_with_ack(sock, message, app_state, target_user["ip"])
        print(f'\n[TICTACTOE] You moved to position {position}\n')

        result = check_game_over(game["board"])
        if result:
            if result == "DRAW":
                print("\n[RESULT] It's a draw!")
                game["status"] = "FINISHED"
            elif result[0] == "WIN":
                print(f"\n[RESULT] You win! Line: {result[1]}")
                game["status"] = "FINISHED"
            del app_state.active_games[game_id]
    except KeyError as e:
        print(f'\n[ERROR] Invalid user_id | {e}\n')
        


# Function to process received move from other user
def handle_move(msg, app_state, sock, sender_ip):
    game_id = msg["GAMEID"]
    turn = int(msg["TURN"])
    pos = int(msg["POSITION"])
    symbol = msg["SYMBOL"]
    sender = msg["FROM"]
    message_id = msg["MESSAGE_ID"]

    key = (game_id, turn)

    with app_state.lock:
        # Check if gameID and turn combination already exists
        if key in app_state.received_moves:
            net_comms.send_ack(sock, message_id, sender_ip) # Send back ack
            return  
        game = app_state.active_games.get(game_id)

        # Create local game from scratch if game not found.
        if not game:
            game = {
                "opponent": sender,
                "symbol": "O" if symbol == "X" else "X",
                "board": [None] * 9,
                "turn": 0,
                "my_turn": False,
                "status": "IN_PROGRESS"
            }
            app_state.active_games[game_id] = game

        
        
        # Check for invalid move
        if pos < 0 or pos > 8 or game["board"][pos] is not None:
            # Invalid move (e.g., cell taken), silently ignore
            net_comms.send_ack(sock, message_id, sender_ip)
            return

        # Accept the move if it's valid
        game["board"][pos] = symbol
        game["turn"] = turn
        game["my_turn"] = True
        app_state.received_moves.add(key)

    net_comms.send_ack(sock, message_id, sender_ip)


    print(f"\n[MOVE] {sender} played {symbol} at {pos}")


    result = check_game_over(game["board"])
    if result:
        if result == "DRAW":
            print("\n[RESULT] It's a draw!")
            game["status"] = "FINISHED"
        elif result[0] == "WIN":
            print(f"\n[RESULT] You lose! Line: {result[1]}")
            game["status"] = "FINISHED"
        del app_state.active_games[game_id]
    



# Function to print the board
def print_board(board):
    symbols = [cell if cell is not None else str(i) for i, cell in enumerate(board)]

    print("\n")
    for i in range(0, 9, 3):
        print(f" {symbols[i]} | {symbols[i+1]} | {symbols[i+2]} ")
    print("\n")

# Function to check game over
def check_game_over(board):
    winning_lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]

    for line in winning_lines:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return ("WIN", line)

    if all(cell is not None for cell in board):
        return "DRAW"

    return None