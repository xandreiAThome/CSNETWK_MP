from datetime import datetime, timezone
import socket
import time
from utils import *
import utils.globals as globals
from follow import handle_follow_message


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
    # print(f"[PROFILE] {display_name}: {status}")
    # Avatar is optional — we ignore AVATAR_* if unsupported
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

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            raw_msg = data.decode('utf-8')
            msg = parse_message(raw_msg)
            msg_type = msg.get("TYPE")

            if msg_type == "PING":
                continue 

            if msg.get("USER_ID") == app_state.user_id:
                continue  # Message is from self
            elif msg_type == "PROFILE":
                handle_profile(msg, addr[0], app_state)
            elif msg_type == "FOLLOW":
                handle_follow_message(msg, app_state)
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)


