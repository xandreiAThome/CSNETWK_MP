# Send message requiring ACK
from datetime import datetime, timezone
import time
from utils.app_state import AppState
from utils.utils import build_message
from utils import globals


def send_with_ack(sock, message: dict, app_state: AppState, ip: str):
    ackable = {
        "TICTACTOE_INVITE",
        "TICTACTOE_MOVE",
        "TICTACTOE_RESULT",
        "DM",
        "FILE_CHUNK",
    }  # Add more message types here
    sock.sendto(build_message(message).encode("utf-8"), (ip, globals.PORT))

    if message["TYPE"] in ackable:
        with app_state.lock:
            app_state.pending_acks[message["MESSAGE_ID"]] = {
                "message": message,
                "destination": ip,
                "retries": 0,
                "timestamp": time.time(),
            }


# Send back ACK
def send_ack(sock, msg_id, target_ip, app_state):
    ack = {"TYPE": "ACK", "MESSAGE_ID": msg_id, "STATUS": "RECEIVED"}
    sock.sendto(build_message(ack).encode("utf-8"), (target_ip, globals.PORT))

    if globals.verbose:
        print(f"\n[SEND >]")
        print(f"Message Type : ACK")
        print(f"Timestamp    : {time.time()}")
        print(f"From IP      : {app_state.user_id.split('@')[1]}")
        print(f"From         : {app_state.user_id}")
        print(f"To           : {target_ip}")
        print(f"MessageID    : {msg_id}")
        print(f"Status       : RECEIVED\n")


def handle_ack(msg, app_state, sender_ip):
    msg_id = msg.get("MESSAGE_ID")
    with app_state.lock:
        if msg_id in app_state.pending_acks:
            del app_state.pending_acks[msg_id]
            print(f"[ACK RECEIVED] {msg_id}")

            if globals.verbose:
                print(f"\n[RECV <]")
                print(f"Message Type : ACK")
                print(f"From IP      : {sender_ip}")
                print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
                print(f"MessageID    : {msg_id}")
                print(f"Status       : {msg.get('STATUS', 'RECEIVED')}\n")
