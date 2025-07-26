from datetime import datetime, timezone
import socket
import time
from utils import *
import utils.globals as globals
from follow import handle_follow_message, handle_unfollow_message
from tictactoe import handle_invite, handle_move, handle_result


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"
    
def send_ping(sock: socket, app_state: AppState):
    message = {
        "TYPE": "PING",
        "USER_ID": app_state.user_id
    }

    sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))

def send_profile(sock: socket, status: str, app_state: AppState):
    message = {
        "TYPE": "PROFILE",
        "USER_ID": app_state.user_id,
        "DISPLAY_NAME": app_state.display_name,
        "STATUS": status,
    }

    sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))
    
def handle_profile(msg: dict, addr:str, app_state: AppState):
    display_name = msg.get("DISPLAY_NAME", "Unknown")
    user_id = msg.get("USER_ID")
    status = msg.get("STATUS", "")

    if user_id not in app_state.peers:
        print(f"\n[PROFILE] (Detected User) {display_name}: {status}", end='\n\n')
    # Avatar is optional — we ignore AVATAR_* if unsupported
    with app_state.lock:
        app_state.peers[user_id] = {
            "ip": addr,
            "display_name": display_name,
            "status": status,
            "last_seen": datetime.now(timezone.utc).timestamp()
        }

def broadcast_loop(sock: socket, app_state: AppState):
    # send profile every 3rd time, else send ping
    count = 0
    while True:
        if count % 3 == 0:
            send_profile(sock,'BROADCASTING', app_state)
            count = 0
        else:
            send_ping(sock, app_state)
        count += 1
        time.sleep(globals.BROADCAST_INTERVAL)

def listener_loop(sock: socket, app_state: AppState):    
    print(f"[LISTENING] UDP port {globals.PORT} on {app_state.local_ip}...\n")
    min_profile_interval = 5  # seconds
    last_profile_time = 0

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            raw_msg = data.decode('utf-8')
            msg = parse_message(raw_msg)
            msg_type = msg.get("TYPE")

            if msg.get("USER_ID") == app_state.user_id:
                continue  # Message is from self
           

            # discovery
              # only send profile if interval has passed, pings just trigger the check
            if msg_type == "PING":
                now = time.time()
                if (now - last_profile_time) > min_profile_interval:
                    send_profile(sock, "BROADCASTING", app_state)
                    last_profile_time = now
                continue
            elif msg_type == "PROFILE":
                handle_profile(msg, addr[0], app_state)
                continue
            
            # ACK
            if msg_type == "ACK":
                handle_ack(msg, app_state, addr[0])
                continue


            # check for core feature msgs that the ip hasnt been spoofed
            # I am crying from the fact that the format of msgs are inconsistent
            # some only have user_id and others have FROM which basically is the user_id of the sender
            # so I need to seperate the if else of PING AND PROFILE from the rest of the msg_types
            # REMINDER that POST also has user_id instead of FROM :-(
            print(msg_type)
            username, user_ip = msg.get("FROM").split('@')
            if user_ip != addr[0]:
                continue

            if msg.get("FROM") == app_state.user_id:
                continue  # Message is from self again, curse the msg formats

            # core features
            if msg_type == "FOLLOW":
                handle_follow_message(msg, app_state)
            elif msg_type == "UNFOLLOW":
                handle_unfollow_message(msg, app_state)
            elif msg_type == "TICTACTOE_INVITE":
                print("[DEBUG] Received INVITE")
                handle_invite(msg, app_state, sock, addr[0])
            elif msg_type == "TICTACTOE_MOVE":
                handle_move(msg, app_state, sock, addr[0])
            elif msg_type == "TICTACTOE_RESULT":
                handle_result(msg, app_state, sock, addr[0])
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)

def ack_resend_loop(sock, app_state):
    while True:
        time.sleep(1)
        with app_state.lock:
            for msg_id, entry in list(app_state.pending_acks.items()):
                if time.time() - entry["timestamp"] > 2:
                    if entry["retries"] >= 3:
                        if globals.verbose:
                            print(f"\n[DROP !]")
                            print(f"MessageID    : {msg_id}")
                            print(f"Reason       : Max retries reached\n")
                        print(f"[ACK] Gave up on {msg_id}")
                        del app_state.pending_acks[msg_id]
                    else:
                        entry["retries"] += 1
                        entry["timestamp"] = time.time()
                        sock.sendto(build_message(entry["message"]).encode("utf-8"), (entry["destination"], globals.PORT))
                        if globals.verbose:
                            print(f"\n[RESEND !]")
                            print(f"Message Type : ACK")
                            print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
                            print(f"From IP      : {app_state.user_id.split('@')[1]}")
                            print(f"From         : {app_state.user_id}")
                            print(f"MessageID    : {msg_id}")
                            print(f"Retry Count  : {entry['retries']}")
                            print(f"Destination  : {entry['destination']}\n")
                        print(f"[RESEND] Retried {msg_id}")


# Send message requiring ACK
def send_with_ack(sock, message: dict, app_state: AppState, ip: str):
    ackable = {"TICTACTOE_INVITE", "TICTACTOE_MOVE", "TICTACTOE_RESULT"} # Add more message types here
    sock.sendto(build_message(message).encode("utf-8"), (ip, globals.PORT))

    if message["TYPE"] in ackable:
        with app_state.lock:
            app_state.pending_acks[message["MESSAGE_ID"]] = {
                "message": message,
                "destination": ip,
                "retries": 0,
                "timestamp": time.time()
            }

# Send back ACK
def send_ack(sock, msg_id, target_ip, app_state):
    ack = {
        "TYPE": "ACK",
        "MESSAGE_ID": msg_id,
        "STATUS": "RECEIVED"
    }
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
            