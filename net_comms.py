from datetime import datetime, timezone
import socket
import time
from utils import *
import globals


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"
    
def send_ping(sock: socket):
    message = {
        "TYPE": "PING",
        "USER_ID": globals.user_id
    }

    sock.sendto(build_message(message).encode('utf-8'), (globals.broadcast_ip, globals.PORT))

def send_profile(sock: socket, status: str):
    message = {
        "TYPE": "PROFILE",
        "USER_ID": globals.user_id,
        "DISPLAY_NAME": globals.display_name,
        "STATUS": status,
    }

    sock.sendto(build_message(message).encode('utf-8'), (globals.broadcast_ip, globals.PORT))

def broadcast_loop(sock: socket):
    # send profile every 3rd time, else send ping
    count = 0
    while True:
        if count % 3 == 0:
            send_profile(sock,'BROADCASTING')
            count = 0
        else:
            send_ping(sock)
        count += 1
        time.sleep(globals.BROADCAST_INTERVAL)

def listener_loop(sock: socket, peers: dict):
    print(f"[LISTENING] UDP port {globals.PORT} on {get_local_ip()}...\n")

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            raw_msg = data.decode('utf-8')
            msg = parse_message(raw_msg)
            msg_type = msg.get("TYPE")

            if msg_type == "PING":
                continue 

            if msg.get("USER_ID") == globals.user_id:
                continue  # Message is from self

            elif msg_type == "PROFILE":
                display_name = msg.get("DISPLAY_NAME", "Unknown")
                user_id = msg.get("USER_ID")
                status = msg.get("STATUS", "")
                print(f"[PROFILE] {display_name}: {status}")
                # Avatar is optional — we ignore AVATAR_* if unsupported
                peers[user_id] = {
                    "ip": addr[0],
                    "display_name": display_name,
                    "status": status,
                    "last_seen": datetime.now(timezone.utc).timestamp()
                }
                print(peers)
            elif msg_type == "FOLLOW":
                display_name = msg.get("DISPLAY_NAME", "Unknown")
                print(f"[FOLLOW] {display_name} followed you")
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)


