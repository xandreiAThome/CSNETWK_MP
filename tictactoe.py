# follow.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *
import net_comms


def send_invite(
    sock: socket, target_user_id: str, app_state: AppState, game_id, symbol
):
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
            "MESSAGE_ID": str(uuid.uuid4().hex[:16]),
            "SYMBOL": symbol,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f"{app_state.user_id}|{timestamp_now + globals.TTL}|game",
        }

        # Store local game state
        with app_state.lock:
            app_state.active_games[game_id] = {
                "opponent": target_user_id,
                "symbol": symbol,
                "board": [None] * 9,
                "turn": 0,
                "my_turn": True,
                "status": "WAITING",
            }

        net_comms.send_with_ack(sock, message, app_state, target_user["ip"])
        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type: TICTACTOE_INVITE")
            print(f"Timestamp: {timestamp_now}")
            print(f"From IP  : {app_state.user_id.split('@')[1]}")
            print(f"From     : {app_state.user_id}")
            print(f"To       : {target_user_id}")
            print(f"Game ID  : {game_id}")
            print(f"MessageID: {message['MESSAGE_ID']}")
            print(f"Symbol   : {symbol}")
            print(f"Token    : {message['TOKEN']}\n")

        print(
            f'\n[TICTACTOE] You invited {target_user["display_name"]} to play Tic Tac Toe (Game ID: {game_id})\n'
        )
    except KeyError as e:
        print(f"\n[ERROR] invalid user_id | {e}", end="\n\n")


# Function to handle received invites
def handle_invite(msg, app_state, sock, sender_ip):
    game_id = msg["GAMEID"]
    sender = msg["FROM"]
    symbol = "O" if msg["SYMBOL"] == "X" else "X"

    if globals.verbose:
        print(f"\n[RECV <]")
        print(f"Message Type : TICTACTOE_INVITE")
        print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
        print(f"From IP      : {sender_ip}")
        print(f"From         : {msg['FROM']}")
        print(f"To           : {msg['TO']}")
        print(f"Game ID      : {msg['GAMEID']}")
        print(f"MessageID    : {msg['MESSAGE_ID']}")
        print(f"Symbol       : {msg['SYMBOL']}")
        print(f"Timestamp    : {msg['TIMESTAMP']}")
        print(f"Token        : {msg['TOKEN']}\n")

    with app_state.lock:
        # Ignore repeated invites
        if game_id in app_state.active_games:
            print("Duplicate invite found.")
            return

        # Store active game
        app_state.active_games[game_id] = {
            "opponent": sender,
            "symbol": symbol,
            "board": [None] * 9,
            "turn": 0,
            "my_turn": False,
            "status": "IN_PROGRESS",
        }

    net_comms.send_ack(sock, msg["MESSAGE_ID"], sender_ip, app_state)

    print(f"\n[INVITE] {sender} invited you to play Tic Tac Toe (Game ID: {game_id})")


# Function to send move to other user
def move(sock: socket, target_user_id: str, app_state: AppState, game_id, position):
    try:
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()
        message_id = uuid.uuid4().hex[:16]

        with app_state.lock:
            # Get active game
            game = app_state.active_games.get(game_id)
            if not game:
                print(f"[ERROR] Game ID {game_id} not found.")
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
            "TOKEN": f"{app_state.user_id}|{timestamp_now + globals.TTL}|game",
        }

        net_comms.send_with_ack(sock, message, app_state, target_user["ip"])
        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type: TICTACTOE_MOVE")
            print(f"Timestamp : {timestamp_now}")
            print(f"From IP   : {app_state.user_id.split('@')[1]}")
            print(f"From      : {app_state.user_id}")
            print(f"To        : {target_user_id}")
            print(f"Game ID   : {game_id}")
            print(f"MessageID : {message['MESSAGE_ID']}")
            print(f"Position  : {position}")
            print(f"Symbol    : {symbol}")
            print(f"Turn      : {game['turn']}")
            print(f"Token     : {message['TOKEN']}\n")

        print(f"\n[TICTACTOE] {game_id}: You moved to position {position}\n")

        result = check_game_over(game["board"])
        if result:
            print_board(board)
            if result == "DRAW":
                print("\n[RESULT] It's a draw!")
                game["status"] = "FINISHED"
                send_result(sock, app_state, target_user_id, game_id, "DRAW")
            elif result[0] == "WIN":
                print(f"\n[RESULT] You win! Line: {result[1]}")
                game["status"] = "FINISHED"
                send_result(sock, app_state, target_user_id, game_id, "WIN", result[1])
            del app_state.active_games[game_id]
    except KeyError as e:
        print(f"\n[ERROR] Invalid user_id | {e}\n")


# Function to process received move from other user
def handle_move(msg, app_state, sock, sender_ip):
    game_id = msg["GAMEID"]
    turn = int(msg["TURN"])
    pos = int(msg["POSITION"])
    symbol = msg["SYMBOL"]
    sender = msg["FROM"]
    message_id = msg["MESSAGE_ID"]

    key = (game_id, turn)

    if globals.verbose:
        print(f"\n[RECV <]")
        print(f"Message Type : TICTACTOE_MOVE")
        print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
        print(f"From IP      : {sender_ip}")
        print(f"From         : {msg['FROM']}")
        print(f"To           : {msg['TO']}")
        print(f"Game ID      : {msg['GAMEID']}")
        print(f"MessageID    : {msg['MESSAGE_ID']}")
        print(f"Position     : {msg['POSITION']}")
        print(f"Symbol       : {msg['SYMBOL']}")
        print(f"Turn         : {msg['TURN']}")
        print(f"Token        : {msg['TOKEN']}\n")

    with app_state.lock:
        # Check if gameID and turn combination already exists
        if key in app_state.received_moves:
            net_comms.send_ack(sock, message_id, sender_ip, app_state)  # Send back ack
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
                "status": "IN_PROGRESS",
            }
            app_state.active_games[game_id] = game

        # Check for invalid move
        if pos < 0 or pos > 8 or game["board"][pos] is not None:
            # Invalid move (e.g., cell taken), silently ignore
            net_comms.send_ack(sock, message_id, sender_ip, app_state)
            return

        # Accept the move if it's valid
        game["board"][pos] = symbol
        game["turn"] = turn
        game["my_turn"] = True
        app_state.received_moves.add(key)

    net_comms.send_ack(sock, message_id, sender_ip, app_state)

    print(f"\n[MOVE] {msg['GAMEID']}: {sender} played {symbol} at {pos}")

    result = check_game_over(game["board"])
    if result:
        print_board(game["board"])
        if result == "DRAW":
            print("\n[RESULT] It's a draw!")
            game["status"] = "FINISHED"
        elif result[0] == "WIN":
            print(f"\n[RESULT] You lose! Line: {result[1]}")
            game["status"] = "FINISHED"
            send_result(sock, app_state, sender, game_id, "LOSS", result[1])
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
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],  # rows
        [0, 3, 6],
        [1, 4, 7],
        [2, 5, 8],  # cols
        [0, 4, 8],
        [2, 4, 6],  # diagonals
    ]

    for line in winning_lines:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return ("WIN", line)

    if all(cell is not None for cell in board):
        return "DRAW"

    return None


def send_result(
    sock, app_state: AppState, target_user_id, game_id, result, winning_line=None
):
    try:
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()
        message_id = str(uuid.uuid4().hex[:16])
        symbol = app_state.active_games[game_id]["symbol"]

        message = {
            "TYPE": "TICTACTOE_RESULT",
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "GAMEID": game_id,
            "MESSAGE_ID": message_id,
            "RESULT": result,
            "SYMBOL": symbol,
            "TIMESTAMP": timestamp_now,
        }

        if winning_line:
            message["WINNING_LINE"] = ",".join(str(i) for i in winning_line)

        net_comms.send_with_ack(sock, message, app_state, target_user["ip"])

        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type : TICTACTOE_RESULT")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From IP  : {app_state.user_id.split('@')[1]}")
            print(f"From         : {app_state.user_id}")
            print(f"To           : {target_user_id}")
            print(f"Game ID      : {game_id}")
            print(f"MessageID    : {message_id}")
            print(f"Result       : {result}")
            print(f"Symbol       : {symbol}")
            if winning_line:
                print(f"Winning Line : {winning_line}")
            print()

    except KeyError as e:
        print(f"[ERROR] Can't send game result: {e}")


def handle_result(
    msg,
    app_state: AppState,
    sock,
    sender_ip,
):
    game_id = msg["GAMEID"]
    result = msg["RESULT"]
    symbol = msg["SYMBOL"]
    winning_line = msg.get("WINNING_LINE")
    message_id = msg["MESSAGE_ID"]

    with app_state.lock:
        if game_id in app_state.active_games:
            del app_state.active_games[game_id]

    if globals.verbose:
        print(f"\n[RECV <]")
        print(f"Message Type : TICTACTOE_RESULT")
        print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
        print(f"From IP      : {sender_ip}")
        print(f"From         : {msg['FROM']}")
        print(f"To           : {msg['TO']}")
        print(f"Game ID      : {game_id}")
        print(f"MessageID    : {message_id}")
        print(f"Result       : {result}")
        print(f"Symbol       : {symbol}")
        if winning_line:
            print(f"Winning Line : {winning_line}")
        print()

    net_comms.send_ack(sock, message_id, sender_ip, app_state)

    if result == "FORFEIT":
        print(f"\n[RESULT] {game_id}: {msg['FROM']} forfeited.")
    else:
        print(f"\n[RESULT] Game {game_id} ended. Result: {msg['FROM']} - {result}")
        if winning_line:
            print(f"Winning Line: {winning_line}")
