import socket
import time
import netifaces
import ipaddress
from utils import *


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"
    
def send_ping(sock: socket, user_id: str, broadcast_ip: str, port: int):
    message = {
        "TYPE": "PING",
        "USER_ID": user_id
    }

    sock.sendto(build_message(message).encode('utf-8'), (broadcast_ip, port))

def send_profile(sock: socket, user_id: str, name: str, status: str, broadcast_ip: str, port: int):
    message = {
        "TYPE": "PROFILE",
        "USER_ID": user_id,
        "DISPLAY_NAME": name,
        "STATUS": status,
    }

    sock.sendto(build_message(message).encode('utf-8'), (broadcast_ip, port))

def broadcast_loop(sock: socket, user_id: str, name: str, broadcast_ip: str, port: int, broadcast_interval: int):
    # send profile every 3rd time, else send ping
    count = 0
    while True:
        if count % 3 == 0:
            send_profile(sock, user_id, name, 'BROADCASTING', broadcast_ip, port)
            count = 0
        else:
            send_ping(sock, user_id, broadcast_ip, port)
        count += 1
        time.sleep(broadcast_interval)

def listener_loop(sock: socket, port: int, user_id: str, peers: dict):
    print(f"[LISTENING] UDP port {port} on {get_local_ip()}...\n")

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            raw_msg = data.decode('utf-8')
            msg = parse_message(raw_msg)
            msg_type = msg.get("TYPE")

            if msg_type == "PING":
                continue 

            if msg.get("USER_ID") == user_id:
                continue  # Message is from self

            elif msg_type == "PROFILE":
                name = msg.get("DISPLAY_NAME", "Unknown")
                status = msg.get("STATUS", "")
                print(f"[PROFILE] {name}: {status}")
                # Avatar is optional — we ignore AVATAR_* if unsupported
                peers[msg.get("USER_ID")] = {
                    "ip": addr[0],
                    "name": name,
                    "status": status,
                    "last_seen": time.time()
                }
                print(peers)
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)


