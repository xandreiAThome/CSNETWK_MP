from datetime import datetime, timezone
import socket
import time
from utils import *
import utils.globals as globals
from follow import handle_follow_message, handle_unfollow_message
from dm import handle_dm
from post import handle_post_message
from like import handle_like_message
from group import handle_create_group, handle_update_group


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
    send_profile(sock, "BROADCASTING", app_state)
    # send profile every 3rd time, else send ping
    while True:
        send_ping(sock, app_state)
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

            # handle cases where the message uses USER_ID instead of FROM
            # failure to handle such cases used to result in errors trying to parse Nonetype
            msg_from = msg.get("FROM")
            msg_user_id = msg.get("USER_ID")

            if not (msg_from is None):
                username, user_ip = msg.get("FROM").split('@')
            elif not (msg_user_id is None):
                username, user_ip = msg.get("USER_ID").split('@')

            # check for core feature msgs that the ip hasnt been spoofed
            # I am crying from the fact that the format of msgs are inconsistent
            # some only have user_id and others have FROM which basically is the user_id of the sender
            # so I need to seperate the if else of PING AND PROFILE from the rest of the msg_types
            # REMINDER that POST also has user_id instead of FROM :-(
            if user_ip != addr[0]:
                continue

            if msg.get("FROM") == app_state.user_id:
                continue  # Message is from self again, curse the msg formats

            print(msg_type)

            # core features
            if msg_type == "FOLLOW":
                handle_follow_message(msg, app_state)
            elif msg_type == "UNFOLLOW":
                handle_unfollow_message(msg, app_state)
            elif msg_type == "POST":
                handle_post_message(msg, app_state)
            elif msg_type == "DM":
                handle_dm(msg, app_state)
            elif msg_type == "LIKE":
                handle_like_message(msg, app_state)
            elif msg_type == "GROUP_CREATE":
                handle_create_group(msg, app_state)
            elif msg_type == "GROUP_UPDATE":
                handle_update_group(msg, app_state)
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)


